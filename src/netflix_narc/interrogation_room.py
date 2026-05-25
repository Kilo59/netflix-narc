"""The Interrogation Room Screen for manual data entry."""

from __future__ import annotations

import urllib.parse
import webbrowser
from typing import TYPE_CHECKING, ClassVar, cast, override

from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Footer, Header, Input, Static

from netflix_narc.csm_api import CSMRatingCategory as CSMCategory
from netflix_narc.manual_db import ManualMetadata

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from netflix_narc.main import NetflixNarcApp


class InterrogationRoomScreen(Screen[bool]):
    """The Interrogation Room Screen: enter manual metadata for a title."""

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("escape", "cancel", "Cancel"),
        Binding("f2", "open_browser", "Search Web"),
        Binding("up", "focus_previous", "Focus Previous", show=False),
        Binding("down", "focus_next", "Focus Next", show=False),
    ]

    def __init__(self, base_title: str) -> None:
        """Initialize the manual entry screen for a specific title."""
        super().__init__()
        self.base_title = base_title
        self.existing_record: ManualMetadata | None = None

    @property
    def narc_app(self) -> NetflixNarcApp:
        """Type-safe access to the main app."""
        return cast("NetflixNarcApp", self.app)

    @override
    def compose(self) -> ComposeResult:
        """Compose the form inputs."""
        yield Header()
        with Container(id="interrogation-container"), Vertical(id="interrogation-card"):
            with Horizontal(id="interrogation-header"):
                yield Static(
                    f"Manual Data Entry for: [b]{self.base_title}[/b]", classes="title-text"
                )
                yield Button("Search Web [F2]", id="btn-search-web", variant="default")

            with Horizontal(classes="form-row"):
                yield Static("Min Age Rating:", classes="form-label")
                yield Input(id="input-age-rating", placeholder="e.g. 13 or TV-14")

            with Horizontal(classes="form-row"):
                yield Static("Quality Rating (1-5):", classes="form-label")
                yield Input(id="input-quality-rating", type="number", placeholder="1-5")

            yield Static("CSM Category Scores (0-5)", classes="section-header")

            with Vertical(id="csm-scores"):
                for cat in CSMCategory:
                    with Horizontal(classes="csm-row"):
                        yield Static(f"{cat.value.replace('_', ' ').title()}:", classes="csm-label")
                        yield Input(id=f"csm-{cat.name}", type="integer", placeholder="0-5")

            yield Checkbox("Flag for future follow-up", id="input-flag")

            with Horizontal(id="interrogation-actions"):
                yield Button("Cancel", id="btn-cancel", variant="default")
                yield Button("Save", id="btn-save", variant="primary")
        yield Footer()

    async def on_mount(self) -> None:
        """Fetch existing data if any, and pre-fill the form."""
        locker = self.narc_app.evidence_locker
        self.existing_record = await locker.get_record(self.base_title)

        if self.existing_record:
            if self.existing_record.content_rating:
                self.query_one("#input-age-rating", Input).value = str(
                    self.existing_record.content_rating
                )
            if self.existing_record.user_rating:
                self.query_one("#input-quality-rating", Input).value = str(
                    self.existing_record.user_rating
                )

            self.query_one(
                "#input-flag", Checkbox
            ).value = self.existing_record.flagged_for_followup

            for cat in CSMCategory:
                score = self.existing_record.category_scores.get(cat.value)
                if score is not None:
                    self.query_one(f"#csm-{cat.name}", Input).value = str(score)

    def action_cancel(self) -> None:
        """Discard changes and close."""
        self.dismiss(False)  # noqa: FBT003

    def action_open_browser(self) -> None:
        """Open the default web browser to search for this title on Common Sense Media."""
        query = urllib.parse.quote_plus(self.base_title)
        url = f"https://www.commonsensemedia.org/search/{query}"
        webbrowser.open(url)
        self.notify(f"Opening browser for: {self.base_title}")

    async def _save_record(self) -> None:
        """Gather values and save to the Evidence Locker."""
        age_val = self.query_one("#input-age-rating", Input).value
        quality_val = self.query_one("#input-quality-rating", Input).value
        is_flagged = self.query_one("#input-flag", Checkbox).value

        age_rating = str(age_val) if age_val else None
        user_rating = float(quality_val) if quality_val else None

        scores: dict[str, float] = {}
        for cat in CSMCategory:
            val = self.query_one(f"#csm-{cat.name}", Input).value
            if val and val.isdigit():
                scores[cat.value] = float(val)

        record = ManualMetadata(
            title=self.base_title,
            content_rating=age_rating,
            user_rating=user_rating,
            flagged_for_followup=is_flagged,
            category_scores=scores,
        )

        await self.narc_app.evidence_locker.upsert_record(record)
        self.notify("Evidence Locker updated!")

        # Optionally update evaluated flags cache so we don't need a full rebuild
        self.narc_app.evaluated_flags.pop(self.base_title, None)

        self.dismiss(True)  # noqa: FBT003

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle save or cancel."""
        if event.button.id == "btn-cancel":
            self.action_cancel()
        elif event.button.id == "btn-save":
            await self._save_record()
        elif event.button.id == "btn-search-web":
            self.action_open_browser()
