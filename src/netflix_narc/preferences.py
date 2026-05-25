"""Always-accessible preferences screen for Netflix Narc."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, cast, override

from pydantic import SecretStr, TypeAdapter
from textual.binding import Binding
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Select, Static, Switch

from netflix_narc.onboarding import (
    _WEIGHT_ROWS,
    WeightRow,
)
from netflix_narc.settings import CategoryWeights, RatingProviderType, parse_str_age_range

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from netflix_narc.main import NetflixNarcApp
    from netflix_narc.settings import Settings


class PreferencesScreen(Screen[None]):
    """Always-accessible full settings panel, bound to S.

    Saves directly via update_env_file and updates app.settings in-memory.
    Escape / Q closes without saving.
    """

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("escape", "dismiss_screen", "Close"),
        Binding("q", "dismiss_screen", "Close"),
    ]

    def __init__(
        self,
        settings: Settings,
    ) -> None:
        """Initialise with current settings."""
        super().__init__()
        self._settings = settings

    @override
    def compose(self) -> ComposeResult:
        """Compose the full preferences screen layout."""
        yield Header()
        with ScrollableContainer(id="prefs-container"):
            yield Static("PREFERENCES", id="prefs-title")

            # ── Profile ──────────────────────────────────────────────
            with Container(classes="pref-section"):
                yield Static("PROFILE", classes="pref-section-header")
                yield Static("Child's age or range  (e.g. 10  or  8-12)", classes="pref-label")
                age_str = ""
                if self._settings.child_age_range is not None:
                    lo, hi = self._settings.child_age_range
                    age_str = f"{lo}-{hi}" if lo != hi else str(lo)
                yield Input(value=age_str, placeholder="e.g. 10  or  8-12", id="pref-age-input")
                yield Static("", id="pref-age-error", classes="pref-error")

            # ── Content Weights ───────────────────────────────────────
            with Container(classes="pref-section"):
                yield Static("CONTENT WEIGHTS", classes="pref-section-header")
                for label, field in _WEIGHT_ROWS:
                    current = getattr(self._settings.weights, field)
                    yield WeightRow(
                        label,
                        field,
                        default=CategoryWeights.DEFAULT_WEIGHTS[field],
                        initial=current,
                    )
                yield Button(
                    "↺ Reset All to Defaults",
                    id="pref-reset-weights",
                    variant="default",
                    classes="pref-reset-btn",
                )

            # ── API / Provider ────────────────────────────────────────
            with Container(classes="pref-section"):
                yield Static("API / PROVIDER  [optional]", classes="pref-section-header")
                yield Static("Rating data provider", classes="pref-label")
                yield Select(
                    [(p.name, p) for p in RatingProviderType],
                    value=self._settings.active_rating_provider,
                    id="pref-provider-select",
                )
                yield Static("API key  (leave blank to keep current)", classes="pref-label")
                yield Input(
                    placeholder="Paste new key, or leave blank",
                    id="pref-api-key-input",
                    password=True,
                )

            # ── Advanced ──────────────────────────────────────────────
            with Container(classes="pref-section"):
                yield Static("ADVANCED", classes="pref-section-header")
                with Horizontal(classes="pref-adv-row"):
                    yield Static("Max records to load", classes="pref-adv-label")
                    yield Input(
                        value=str(self._settings.max_records),
                        id="pref-max-records",
                        classes="pref-adv-input",
                    )
                with Horizontal(classes="pref-adv-row"):
                    yield Static("Min quality rating (CSM stars)", classes="pref-adv-label")
                    yield Input(
                        value=str(self._settings.min_quality_rating),
                        id="pref-min-quality",
                        classes="pref-adv-input",
                    )
                with Horizontal(classes="pref-adv-row"):
                    yield Static("Max age rating", classes="pref-adv-label")
                    yield Input(
                        value=str(self._settings.max_age_rating),
                        id="pref-max-age",
                        classes="pref-adv-input",
                    )
                with Horizontal(classes="pref-adv-row"):
                    yield Static("Merge Evidence Locker data", classes="pref-adv-label")
                    yield Switch(
                        value=self._settings.merge_manual_data,
                        id="pref-merge-switch",
                    )

            # ── Action buttons ────────────────────────────────────────
            with Horizontal(id="prefs-actions"):
                yield Button("Save", id="pref-save", variant="primary")
                yield Button("Re-launch Setup Wizard", id="pref-relaunch", variant="default")
                yield Button("Close", id="pref-close", variant="default")

        yield Footer()

    # ── Button handling ───────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle Save, Close, and Reset All Weights button presses."""
        btn_id = event.button.id or ""

        if btn_id == "pref-save":
            self._save()
        elif btn_id == "pref-close":
            self.dismiss()
        elif btn_id == "pref-relaunch":
            self.dismiss()
            # Launch onboarding relaunch in the main app context
            narc_app = cast("NetflixNarcApp", self.app)
            narc_app.call_after_refresh(narc_app.push_onboarding_relaunch)
        elif btn_id == "pref-reset-weights":
            self._reset_weights()

    def action_dismiss_screen(self) -> None:
        """Close preferences without saving."""
        self.dismiss()

    def _reset_weights(self) -> None:
        """Reset all weight rows to factory defaults."""
        for row in self.query(WeightRow):
            row.value = CategoryWeights.DEFAULT_WEIGHTS[row.field_name]
            row.refresh_buttons()

    # ── Save helpers ──────────────────────────────────────────────────────

    def _collect_age(self) -> tuple[int, int] | None:
        """Parse and return the new age range, or None if invalid/unchanged."""
        age_raw = self.query_one("#pref-age-input", Input).value.strip()
        if not age_raw:
            return self._settings.child_age_range
        try:
            new_age = parse_str_age_range(age_raw)
        except ValueError:
            new_age = None
        if new_age is None:
            self.query_one("#pref-age-error", Static).update(
                "[red]Invalid age range (e.g. 10 or 8-12)[/red]"
            )
            return None
        return new_age

    def _collect_weights(self) -> CategoryWeights:
        """Collect current WeightRow values into a CategoryWeights instance."""
        kwargs: dict[str, int] = {}
        for row in self.query(WeightRow):
            kwargs[row.field_name] = row.value
        return CategoryWeights(**kwargs)

    def _collect_provider_and_key(self) -> tuple[RatingProviderType, SecretStr]:
        """Return the selected provider and API key (falling back to stored key)."""
        provider_select = cast(
            "Select[RatingProviderType]",
            self.query_one("#pref-provider-select", Select),
        )
        pv = provider_select.value
        new_provider = (
            pv if isinstance(pv, RatingProviderType) else self._settings.active_rating_provider
        )
        key_raw = self.query_one("#pref-api-key-input", Input).value.strip()
        if key_raw:
            return new_provider, TypeAdapter(SecretStr).validate_python(key_raw)
        # Keep currently stored key for this provider
        stored: SecretStr
        if new_provider == RatingProviderType.CSM:
            stored = self._settings.csm_api_key
        elif new_provider == RatingProviderType.OMDB:
            stored = self._settings.omdb_api_key
        else:
            stored = self._settings.tmdb_api_key
        return new_provider, stored

    def _collect_advanced(self) -> tuple[int, int, int, bool]:
        """Return (max_records, min_quality, max_age, merge_manual) from advanced fields."""

        def _int(widget_id: str, fallback: int) -> int:
            try:
                return int(self.query_one(widget_id, Input).value)
            except ValueError:
                return fallback

        return (
            _int("#pref-max-records", self._settings.max_records),
            _int("#pref-min-quality", self._settings.min_quality_rating),
            _int("#pref-max-age", self._settings.max_age_rating),
            self.query_one("#pref-merge-switch", Switch).value,
        )

    def _save(self) -> None:
        """Validate, persist, and update in-memory settings, then dismiss."""
        from netflix_narc.persistence import update_env_file  # noqa: PLC0415

        new_age = self._collect_age()
        if new_age is None and self.query_one("#pref-age-input", Input).value.strip():
            return  # age error already set by _collect_age

        new_weights = self._collect_weights()
        new_provider, new_key = self._collect_provider_and_key()
        new_max_records, new_min_quality, new_max_age, new_merge = self._collect_advanced()

        update_env_file(
            provider=new_provider,
            api_key=new_key,
            child_age_range=new_age,
            weights=new_weights,
        )

        # Update in-memory settings
        self._settings.active_rating_provider = new_provider
        self._settings.child_age_range = new_age
        self._settings.weights = new_weights
        self._settings.max_records = new_max_records
        self._settings.min_quality_rating = new_min_quality
        self._settings.max_age_rating = new_max_age
        self._settings.merge_manual_data = new_merge
        match new_provider:
            case RatingProviderType.CSM:
                self._settings.csm_api_key = new_key
            case RatingProviderType.OMDB:
                self._settings.omdb_api_key = new_key
            case RatingProviderType.TMDB:
                self._settings.tmdb_api_key = new_key

        self.app.notify("Preferences saved.", severity="information")
        self.dismiss()
