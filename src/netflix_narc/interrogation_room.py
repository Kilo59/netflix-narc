"""The Interrogation Room Screen for manual data entry."""

from __future__ import annotations

import contextlib
import pathlib
import urllib.parse
import webbrowser
from typing import TYPE_CHECKING, ClassVar, cast, override

from rich_pixels import Pixels
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Footer, Header, Input, Static

from netflix_narc.csm_api import CSMRatingCategory as CSMCategory
from netflix_narc.evaluator import (
    calculate_suitability,
    explain_suitability,
    get_age_suitability_deduction,
    get_categories_suitability_deduction,
    get_edu_suitability_deduction,
    get_suitability_bar,
)
from netflix_narc.image_utils import download_image_to_path, save_image_from_clipboard
from netflix_narc.manual_db import ManualMetadata
from netflix_narc.rating_api import NormalizedMetadata

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from netflix_narc.main import NetflixNarcApp


class InterrogationRoomScreen(Screen[bool]):
    """The Interrogation Room Screen: enter manual metadata for a title."""

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("escape", "save_and_exit", "Save & Exit"),
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

            with Vertical(id="suitability-dashboard"):
                yield Static("", id="overall-suitability-bar", classes="suitability-bar-main")
                yield Static("", id="base-quality-bar", classes="suitability-bar-sub")
                yield Static("", id="age-suitability-bar", classes="suitability-bar-sub")
                yield Static("", id="edu-suitability-bar", classes="suitability-bar-sub")
                yield Static("", id="content-suitability-bar", classes="suitability-bar-sub")

            with Horizontal(classes="form-row"):
                yield Static("Min Age Rating:", classes="form-label")
                yield Input(id="input-age-rating", placeholder="e.g. 13 or TV-14")

            with Horizontal(classes="form-row"):
                yield Static("Quality Rating (1-5):", classes="form-label")
                yield Input(id="input-quality-rating", type="number", placeholder="1-5")

            with Horizontal(classes="form-row-image"):
                yield Static("Cover Image:", classes="form-label")
                yield Input(id="input-image-url", placeholder="Image URL...")
                yield Button("Paste", id="btn-paste-image", variant="success")

            yield Static(id="image-preview", classes="hidden")

            yield Static("CSM Category Scores (0-5)", classes="section-header")

            with Vertical(id="csm-scores"):
                for cat in CSMCategory:
                    with Horizontal(classes="csm-row"):
                        yield Static(f"{cat.value.replace('_', ' ').title()}:", classes="csm-label")
                        yield Input(id=f"csm-{cat.name}", type="integer", placeholder="0-5")

            yield Checkbox("Flag for future follow-up", id="input-flag")

            with Horizontal(id="interrogation-actions"):
                yield Button("Discard Changes", id="btn-cancel", variant="error")
                yield Button("Save & Exit", id="btn-save", variant="primary")
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
            if self.existing_record.user_rating is not None:
                # DB stores normalized 0-10 scale; UI expects 1-5
                display_val = self.existing_record.user_rating / 2
                # If it's a whole number like 4.0, format it as "4" for aesthetics
                display_str = f"{display_val:g}"
                self.query_one("#input-quality-rating", Input).value = display_str
            if self.existing_record.image_url:
                self.query_one("#input-image-url", Input).value = str(
                    self.existing_record.image_url
                )
                self._update_image_preview(self.existing_record.image_url)

            self.query_one(
                "#input-flag", Checkbox
            ).value = self.existing_record.flagged_for_followup

            for cat in CSMCategory:
                score = self.existing_record.category_scores.get(cat.value)
                if score is not None:
                    self.query_one(f"#csm-{cat.name}", Input).value = str(score)

        self._update_realtime_suitability()

    def action_cancel(self) -> None:
        """Discard changes and close."""
        self.dismiss(False)  # noqa: FBT003

    async def action_save_and_exit(self) -> None:
        """Save changes and close."""
        await self._save_record()

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
        image_url_val = self.query_one("#input-image-url", Input).value
        is_flagged = self.query_one("#input-flag", Checkbox).value

        # Handle Image Download if it's an HTTP URL
        if image_url_val and image_url_val.startswith("http"):
            self.notify("Downloading image...")
            local_path = await download_image_to_path(image_url_val, self.base_title)
            if local_path:
                image_url_val = str(local_path)
            else:
                self.notify("Failed to download image.", severity="error")

        age_rating = str(age_val) if age_val else None
        # Convert UI 1-5 rating into normalized 0-10 DB rating
        user_rating = (float(quality_val) * 2) if quality_val else None
        final_image_url = str(image_url_val) if image_url_val else None

        scores: dict[str, float] = {}
        for cat in CSMCategory:
            val = self.query_one(f"#csm-{cat.name}", Input).value
            if val:
                with contextlib.suppress(ValueError):
                    scores[cat.value] = float(val)

        record = ManualMetadata(
            title=self.base_title,
            content_rating=age_rating,
            user_rating=user_rating,
            image_url=final_image_url,
            flagged_for_followup=is_flagged,
            category_scores=scores,
        )

        await self.narc_app.evidence_locker.upsert_record(record)
        self.notify("Evidence Locker updated!")

        # Instantly update the main table with the new manual data flags
        await self.narc_app.refresh_title(self.base_title)

        self.dismiss(True)  # noqa: FBT003

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle save or cancel."""
        if event.button.id == "btn-cancel":
            self.action_cancel()
        elif event.button.id == "btn-save":
            await self._save_record()
        elif event.button.id == "btn-search-web":
            self.action_open_browser()
        elif event.button.id == "btn-paste-image":
            await self._paste_image()

    async def _paste_image(self) -> None:
        """Paste image from OS clipboard and save locally."""
        filepath = await save_image_from_clipboard(self.base_title)
        if filepath:
            self.query_one("#input-image-url", Input).value = str(filepath)
            self._update_image_preview(str(filepath))
            self.notify("Image pasted and saved locally!")
        else:
            self.notify(
                "Failed to paste image. Is there an image in your clipboard?",
                severity="error",
            )

    def _update_image_preview(self, path_or_url: str) -> None:
        """Update the image preview if the path is a valid local file."""
        preview = self.query_one("#image-preview", Static)
        if not path_or_url or path_or_url.startswith("http"):
            preview.display = False
            return

        path = pathlib.Path(path_or_url)
        if path.exists() and path.is_file():
            try:
                # Resize the image so it fits reasonably in the TUI without taking over the screen
                pixels = Pixels.from_image_path(str(path), resize=(35, 25))
                preview.update(pixels)
                preview.display = True
            except (OSError, ValueError) as e:
                self.notify(f"Could not render image: {e}", severity="warning")
                preview.display = False
        else:
            preview.display = False

    def _update_realtime_suitability(self) -> None:
        """Read all inputs in real-time, compute suitability, and update the display bar."""
        age_str = self.query_one("#input-age-rating", Input).value.strip()
        quality_str = self.query_one("#input-quality-rating", Input).value.strip()

        # Quality converts UI 1-5 to normalized 0-10 scale (double it)
        user_rating = None
        if quality_str:
            with contextlib.suppress(ValueError):
                user_rating = float(quality_str) * 2

        scores: dict[str, int | float] = {}
        for cat in CSMCategory:
            val = self.query_one(f"#csm-{cat.name}", Input).value.strip()
            if val:
                with contextlib.suppress(ValueError):
                    scores[cat.value] = float(val)

        # Build temporary metadata object
        metadata = NormalizedMetadata(
            title=self.base_title,
            content_rating=age_str or None,
            user_rating=user_rating,
            provider_name="manual",
            category_scores=scores,
        )

        # Calculate score and update the bar widgets
        score = calculate_suitability(metadata, self.narc_app.settings)
        overall_bar = get_suitability_bar(score, width=20)
        self.query_one("#overall-suitability-bar", Static).update(
            f"Overall Suitability:  {overall_bar}"
        )

        # 2. Base Quality
        base_val = metadata.user_rating if metadata.user_rating is not None else 5.0
        base_bar = get_suitability_bar(base_val, width=15)
        self.query_one("#base-quality-bar", Static).update(f"  └─ Base Quality:     {base_bar}")

        # 3. Age Rating Suitability
        age_ded = get_age_suitability_deduction(
            metadata.content_rating, self.narc_app.settings.max_age_rating
        )
        # Normalize age suitability out of 10
        age_val = max(0.0, 10.0 - age_ded * 2.0)
        age_bar = get_suitability_bar(age_val, width=15)
        self.query_one("#age-suitability-bar", Static).update(f"  └─ Age Rating:       {age_bar}")

        # 4. Educational Value
        edu_score = scores.get("Educational Value")
        edu_ded = get_edu_suitability_deduction(
            edu_score, metadata.user_rating, self.narc_app.settings.min_quality_rating
        )
        # Normalize edu suitability out of 10
        edu_val = max(0.0, 10.0 - edu_ded * 3.33)
        edu_bar = get_suitability_bar(edu_val, width=15)
        self.query_one("#edu-suitability-bar", Static).update(f"  └─ Educational Value:{edu_bar}")

        # 5. Content Safety (negative categories)
        content_ded = get_categories_suitability_deduction(
            metadata.category_scores, self.narc_app.settings
        )
        # Normalize content suitability out of 10
        content_val = max(0.0, 10.0 - content_ded * 1.0)
        content_bar = get_suitability_bar(content_val, width=15)
        self.query_one("#content-suitability-bar", Static).update(
            f"  └─ Content Safety:   {content_bar}"
        )

        # Calculate detailed explanations for tooltip
        explanations = explain_suitability(metadata, self.narc_app.settings)
        tooltip_lines = [
            f"Detailed Score Breakdown for: {self.base_title}",
            "========================================",
        ]
        tooltip_lines.extend(explanations)
        tooltip_lines.append("========================================")
        tooltip_lines.append(f"Final Suitability Score: {score:.1f}/10")
        tooltip_text = "\n".join(tooltip_lines)

        self.query_one("#suitability-dashboard", Vertical).tooltip = tooltip_text

    def on_input_changed(self, _event: Input.Changed) -> None:
        """Handle real-time updates of suitability score when inputs change."""
        self._update_realtime_suitability()
