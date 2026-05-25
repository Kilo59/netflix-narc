"""First-run multi-step onboarding wizard for Netflix Narc."""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, ClassVar, NamedTuple, cast, override

from pydantic import SecretStr, TypeAdapter
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Button, Footer, Header, Input, Select, Static

from netflix_narc.evaluator import calculate_suitability, get_suitability_bar
from netflix_narc.settings import (
    CategoryWeights,
    RatingProviderType,
    parse_str_age_range,
)

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from netflix_narc.manual_db import ManualMetadata
    from netflix_narc.settings import Settings


# ──────────────────────────────────────────────
# Return type
# ──────────────────────────────────────────────


class OnboardingResult(NamedTuple):
    """Result returned by OnboardingScreen on completion."""

    child_age_range: tuple[int, int]
    weights: CategoryWeights
    provider: RatingProviderType | None  # None = skipped
    api_key: SecretStr | None  # None = skipped


# ──────────────────────────────────────────────
# WeightRow composite widget
# ──────────────────────────────────────────────

_WEIGHT_LABELS: dict[int, str] = {1: "Low", 2: "Med", 3: "High"}
_WEIGHT_MIN = 1
_WEIGHT_MAX = 3


class WeightRow(Widget):
    """A single category weight row: label + Low/Med/High toggle buttons + reset."""

    DEFAULT_CSS = """
    WeightRow {
        height: 3;
        layout: horizontal;
        align: left middle;
    }
    WeightRow .wr-label {
        width: 28;
        content-align: left middle;
        color: #E5E5E5;
    }
    WeightRow .wr-btn {
        width: 7;
        min-width: 7;
        margin: 0 0;
        background: #333333;
        color: #808080;
        border: none;
    }
    WeightRow .wr-btn.-primary {
        background: #E50914;
        color: #FFFFFF;
    }
    WeightRow .wr-reset {
        width: 4;
        min-width: 4;
        margin-left: 1;
        background: #1e1e1e;
        color: #555555;
        border: none;
    }
    WeightRow .wr-reset:hover {
        color: #E5E5E5;
    }
    """

    class Changed(Message):
        """Posted when the weight value changes."""

        def __init__(self, row: WeightRow, value: int) -> None:
            """Initialise with the changed row and its new value."""
            super().__init__()
            self.row = row
            self.value = value

    value: reactive[int] = reactive(1)

    def __init__(
        self,
        label: str,
        field_name: str,
        default: int,
        initial: int | None = None,
    ) -> None:
        """Initialise the row with its label, field name, default and optional current value."""
        super().__init__()
        self.label = label
        self.field_name = field_name
        self.default = default
        self._initial = initial if initial is not None else default

    def on_mount(self) -> None:
        """Set initial value after mount so reactive is ready."""
        self.value = self._initial
        self._refresh_buttons()

    @override
    def compose(self) -> ComposeResult:
        yield Static(self.label, classes="wr-label")
        for w in (_WEIGHT_MIN, 2, _WEIGHT_MAX):
            yield Button(_WEIGHT_LABELS[w], id=f"wr-{self.field_name}-{w}", classes="wr-btn")
        yield Button("↺", id=f"wr-{self.field_name}-reset", classes="wr-reset")

    def _refresh_buttons(self) -> None:
        for w in (_WEIGHT_MIN, 2, _WEIGHT_MAX):
            btn = self.query_one(f"#wr-{self.field_name}-{w}", Button)
            if w == self.value:
                btn.variant = "primary"
            else:
                btn.variant = "default"

    def refresh_buttons(self) -> None:
        """Public alias for _refresh_buttons; use when updating value externally."""
        self._refresh_buttons()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Toggle the active weight or reset to the row default."""
        btn_id = event.button.id or ""
        if btn_id == f"wr-{self.field_name}-reset":
            self.value = self.default
        else:
            for w in (_WEIGHT_MIN, 2, _WEIGHT_MAX):
                if btn_id == f"wr-{self.field_name}-{w}":
                    self.value = w
                    break
        self._refresh_buttons()
        self.post_message(WeightRow.Changed(self, self.value))
        event.stop()


# ──────────────────────────────────────────────
# WeightImpactPreview widget
# ──────────────────────────────────────────────

_COMPLETENESS_THRESHOLD = 70
_MAX_PREVIEW_TITLES = 6
_MIN_PREVIEW_TITLES = 2
_DELTA_EPSILON = 0.05
_TITLE_MAX_LEN = 25


def _sample_indices(total: int, n: int) -> list[int]:
    """Return n evenly-spaced indices covering 0..total-1 inclusive."""
    if total <= n:
        return list(range(total))
    step = (total - 1) / (n - 1)
    return [round(i * step) for i in range(n)]


class WeightImpactPreview(Widget):
    """Live before/after suitability preview for a sample of Evidence Locker titles."""

    DEFAULT_CSS = """
    WeightImpactPreview {
        width: 1fr;
        height: auto;
        border-left: solid #333333;
        padding: 0 1;
    }
    WeightImpactPreview .wip-title {
        color: #E50914;
        text-style: bold;
        margin-bottom: 1;
    }
    WeightImpactPreview .wip-hint {
        color: #555555;
        margin-top: 1;
    }
    WeightImpactPreview .wip-entry-title {
        text-style: bold;
        color: #E5E5E5;
        margin-top: 1;
    }
    WeightImpactPreview .wip-bars {
        color: #808080;
    }
    WeightImpactPreview .wip-footer {
        color: #444444;
        margin-top: 1;
    }
    WeightImpactPreview #wip-pin-select {
        margin-bottom: 1;
        height: 3;
    }
    """

    def __init__(
        self,
        preview_records: list[ManualMetadata],
        baseline_settings: Settings,
        all_eligible: list[ManualMetadata] | None = None,
    ) -> None:
        """Initialise with sampled records, baseline settings, and the full eligible pool."""
        super().__init__()
        self._records = preview_records
        self._baseline_settings = baseline_settings
        self._all_eligible: list[ManualMetadata] = all_eligible or []
        self._pinned: ManualMetadata | None = None
        self._current_weights = CategoryWeights(**CategoryWeights.DEFAULT_WEIGHTS)

    @override
    def compose(self) -> ComposeResult:
        """Compose the preview panel: title, optional pin-select, and body."""
        yield Static("WEIGHT IMPACT PREVIEW", classes="wip-title")
        if len(self._all_eligible) >= _MIN_PREVIEW_TITLES:
            options: list[tuple[str, str]] = [(r.title, r.title) for r in self._all_eligible]
            yield Select(
                options,
                prompt="📌 Pin a title…",
                id="wip-pin-select",
                allow_blank=True,
            )
        yield Static("", id="wip-body")

    def on_mount(self) -> None:
        """Render the initial preview on mount."""
        self._render_preview(self._current_weights)

    def on_weight_row_changed(self, event: WeightRow.Changed) -> None:  # noqa: ARG002
        """Rebuild the preview whenever any weight changes."""
        # Read all sibling WeightRow widgets to get the full current state
        rows = self.screen.query(WeightRow)
        kwargs: dict[str, int] = {}
        for row in rows:
            kwargs[row.field_name] = row.value
        self._current_weights = CategoryWeights(**kwargs)
        self._render_preview(self._current_weights)

    def on_select_changed(self, event: Select.Changed) -> None:
        """Pin or unpin a specific title in the impact preview."""
        event.stop()
        if event.select.id != "wip-pin-select":
            return
        if event.value is Select.BLANK:
            self._pinned = None
        else:
            self._pinned = next((r for r in self._all_eligible if r.title == event.value), None)
        self._render_preview(self._current_weights)

    def _render_preview(self, live_weights: CategoryWeights) -> None:
        body = self.query_one("#wip-body", Static)

        # Build display list: pinned title first (always), then sampled (deduped)
        display: list[tuple[ManualMetadata, bool]] = []  # (record, is_pinned)
        if self._pinned is not None:
            display.append((self._pinned, True))
        display.extend(
            (r, False)
            for r in self._records
            if self._pinned is None or r.title != self._pinned.title
        )
        display = display[:_MAX_PREVIEW_TITLES]

        if len(display) < _MIN_PREVIEW_TITLES:
            body.update(
                "[dim]Complete more title dossiers (\u226570%)\nto unlock the impact preview.[/dim]"
            )
            return

        lines: list[str] = []
        live_settings = copy.copy(self._baseline_settings)
        live_settings.weights = live_weights

        for record, is_pinned in display:
            meta = record.to_normalized_metadata()
            before = calculate_suitability(meta, self._baseline_settings)
            after = calculate_suitability(meta, live_settings)
            delta = after - before

            raw_title = record.title
            if len(raw_title) > _TITLE_MAX_LEN:
                raw_title = raw_title[:24] + "\u2026"
            pin_mark = "\U0001f4cc " if is_pinned else ""
            title_display = f"{pin_mark}{raw_title}"

            before_bar = get_suitability_bar(before, width=8)
            after_bar = get_suitability_bar(after, width=8)

            if abs(delta) < _DELTA_EPSILON:
                delta_str = "[dim]\u2014[/dim]"
            elif delta > 0:
                delta_str = f"[green]\u2191 +{delta:.1f}[/green]"
            else:
                delta_str = f"[red]\u2193 {delta:.1f}[/red]"

            lines.append(f"[bold]{title_display}[/bold]")
            lines.append(f"  {before_bar} \u2192 {after_bar}  {delta_str}")

        count = len(display)
        lines.append(
            f"\n[dim]{count} titles  \u2022  \u2265{_COMPLETENESS_THRESHOLD}% complete[/dim]"
        )
        body.update("\n".join(lines))

    @classmethod
    def get_eligible_records(
        cls,
        all_records: list[ManualMetadata],
        baseline_settings: Settings,
    ) -> list[ManualMetadata]:
        """Return all records with completeness >= threshold, sorted by suitability score."""
        return sorted(
            [
                r
                for r in all_records
                if r.completeness_score >= _COMPLETENESS_THRESHOLD and not r.ignored
            ],
            key=lambda r: calculate_suitability(r.to_normalized_metadata(), baseline_settings),
        )

    @classmethod
    def select_preview_records(
        cls,
        all_records: list[ManualMetadata],
        baseline_settings: Settings,
    ) -> list[ManualMetadata]:
        """Filter, score, sort and sample records for the preview panel."""
        eligible = cls.get_eligible_records(all_records, baseline_settings)
        if len(eligible) < _MIN_PREVIEW_TITLES:
            return eligible  # will trigger the graceful-hide path

        n = min(_MAX_PREVIEW_TITLES, len(eligible))
        indices = _sample_indices(len(eligible), n)
        return [eligible[i] for i in indices]


# ──────────────────────────────────────────────
# OnboardingScreen
# ──────────────────────────────────────────────

_STEPS = ["step-welcome", "step-age", "step-weights", "step-api", "step-summary"]
_STEP_LABELS = ["Welcome", "Age", "Weights", "Provider", "Ready"]

_WEIGHT_ROWS: list[tuple[str, str]] = [
    ("Educational Value", "educational_value"),
    ("Positive Messages", "positive_messages"),
    ("Positive Role Models", "positive_role_models"),
    ("Violence & Scariness", "violence"),
    ("Sexy Stuff", "sexy_stuff"),
    ("Language", "language"),
    ("Drinking, Drugs & Smoking", "drinking_drugs"),
]


class OnboardingScreen(Screen[OnboardingResult | None]):
    """Multi-step first-run wizard.

    Shown only when child_age_range is None.
    Escape cancels → returns None → app exits.
    """

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(
        self,
        preview_records: list[ManualMetadata] | None = None,
        baseline_settings: Settings | None = None,
        all_eligible: list[ManualMetadata] | None = None,
    ) -> None:
        """Initialise the wizard with optional preview, baseline settings, and eligible pool."""
        super().__init__()
        self._preview_records: list[ManualMetadata] = preview_records or []
        self._baseline_settings = baseline_settings
        self._all_eligible: list[ManualMetadata] = all_eligible or []
        self._current_step = 0
        self._child_age_range: tuple[int, int] | None = None
        self._age_valid = False

    @override
    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="onboarding-container"), Vertical(id="onboarding-card"):
            yield Static("", id="step-indicator")
            # Step 0: Welcome
            with Container(id="step-welcome"):
                yield Static("NETFLIX NARC", classes="onb-title")
                yield Static(
                    "Know what your family is actually watching.",
                    classes="onb-subtitle",
                )
                yield Static(
                    "This quick setup takes about a minute.\n"
                    "You can change everything later via Preferences [S].",
                    classes="onb-body",
                )
            # Step 1: Age
            with Container(id="step-age", classes="hidden"):
                yield Static("CHILD'S AGE", classes="onb-title")
                yield Static(
                    "Enter your child's age or range (e.g. 10 or 8-12).\n"
                    "This sets the age-rating threshold used in all evaluations.",
                    classes="onb-body",
                )
                yield Input(
                    placeholder="e.g. 10  or  8-12",
                    id="age-input",
                )
                yield Static("", id="age-error", classes="onb-error")
            # Step 2: Weights
            with Container(id="step-weights", classes="hidden"):  # noqa: SIM117
                with Horizontal(id="weights-layout"):
                    with Vertical(id="weights-left"):
                        yield Static("CONTENT WEIGHTS", classes="onb-section-title")
                        yield Static(
                            "How strictly should each category be penalised?\n"
                            "You can always adjust these later.",
                            classes="onb-body",
                        )
                        for label, field in _WEIGHT_ROWS:
                            yield WeightRow(
                                label,
                                field,
                                default=CategoryWeights.DEFAULT_WEIGHTS[field],
                            )
                        yield Button(
                            "↺ Reset All to Defaults",
                            id="btn-reset-all-weights",
                            variant="default",
                            classes="onb-reset-btn",
                        )
                    # Preview panel — only rendered if we have eligible records
                    has_preview = (
                        len(self._preview_records) >= _MIN_PREVIEW_TITLES
                        and self._baseline_settings is not None
                    )
                    if has_preview and self._baseline_settings is not None:
                        yield WeightImpactPreview(
                            self._preview_records,
                            self._baseline_settings,
                            all_eligible=self._all_eligible,
                        )
            # Step 3: API
            with Container(id="step-api", classes="hidden"):
                yield Static("API PROVIDER  [optional]", classes="onb-title")
                yield Static(
                    "Add an API key to fetch ratings automatically.\n"
                    "This is optional — you can skip and enter data manually.",
                    classes="onb-body",
                )
                yield Select(
                    [(p.name.replace("_", " "), p) for p in RatingProviderType],
                    value=RatingProviderType.OMDB,
                    id="provider-select",
                )
                yield Input(
                    placeholder="Paste API key here (optional)…",
                    id="api-key-input",
                    password=True,
                )
            # Step 4: Summary
            with Container(id="step-summary", classes="hidden"):
                yield Static("ALL SET!", classes="onb-title")
                yield Static("", id="summary-body", classes="onb-body")

            # Navigation footer
            with Horizontal(id="onb-nav"):
                yield Button("← Back", id="btn-back", variant="default")
                yield Button("Skip →", id="btn-skip", variant="default", classes="hidden")
                yield Button("Next →", id="btn-next", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        """Initialise the wizard on the first step."""
        self._go_to_step(0)

    # ── Navigation ────────────────────────────────────────────────────────

    def _go_to_step(self, step: int) -> None:
        self._current_step = step
        for i, step_id in enumerate(_STEPS):
            container = self.query_one(f"#{step_id}", Container)
            if i == step:
                container.remove_class("hidden")
            else:
                container.add_class("hidden")

        back_btn = self.query_one("#btn-back", Button)
        next_btn = self.query_one("#btn-next", Button)
        skip_btn = self.query_one("#btn-skip", Button)

        back_btn.disabled = step == 0
        back_btn.display = step > 0

        # Optional steps show Skip instead of dimming Next
        is_optional = step in (2, 3)
        skip_btn.display = is_optional

        if step == len(_STEPS) - 1:
            next_btn.label = "Start Narcing →"
        elif step == 0:
            next_btn.label = "Let's Go →"
        else:
            next_btn.label = "Next →"

        if step == 1:
            next_btn.disabled = not self._age_valid
        else:
            next_btn.disabled = False

        if step == len(_STEPS) - 1:
            self._populate_summary()

        self._update_indicator()

    def _update_indicator(self) -> None:
        dots = ""
        for i in range(len(_STEPS)):
            if i == self._current_step:
                dots += "[#E50914]●[/#E50914]"
            else:
                dots += "[#444444]●[/#444444]"
            if i < len(_STEPS) - 1:
                dots += " "
        label = _STEP_LABELS[self._current_step]
        indicator = self.query_one("#step-indicator", Static)
        indicator.update(f"{dots}   [dim]{label}[/dim]")

    def _populate_summary(self) -> None:
        weights = self._collect_weights()
        age = self._child_age_range
        age_str = (
            f"{age[0]}-{age[1]}" if age and age[0] != age[1] else str(age[0]) if age else "Not set"
        )
        provider = cast("Select[RatingProviderType]", self.query_one("#provider-select", Select))
        api_key_val = self.query_one("#api-key-input", Input).value.strip()
        provider_str: str
        if provider.value and api_key_val and isinstance(provider.value, RatingProviderType):
            provider_str = provider.value.upper()
        else:
            provider_str = "Manual only"
        w_lines = "\n".join(
            f"  {lbl}: {_WEIGHT_LABELS[getattr(weights, field)]}" for lbl, field in _WEIGHT_ROWS
        )
        body = (
            f"Child age range:  {age_str}\n"
            f"Provider:         {provider_str}\n\n"
            f"Content weights:\n{w_lines}"
        )
        self.query_one("#summary-body", Static).update(body)

    # ── Button handling ───────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:  # noqa: C901
        """Handle button presses for navigation and weight reset."""
        btn_id = event.button.id or ""
        if btn_id == "btn-next":
            if self._current_step == len(_STEPS) - 1:
                self._finish()
            else:
                if self._current_step == 1 and not self._validate_age():
                    return
                self._go_to_step(self._current_step + 1)

        elif btn_id == "btn-back":
            if self._current_step > 0:
                self._go_to_step(self._current_step - 1)

        elif btn_id == "btn-skip":
            self._go_to_step(self._current_step + 1)

        elif btn_id == "btn-reset-all-weights":
            for row in self.query(WeightRow):
                row.value = CategoryWeights.DEFAULT_WEIGHTS[row.field_name]
                row.refresh_buttons()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Validate age input as the user types and enable/disable Next."""
        if event.input.id == "age-input":
            self._age_valid = self._check_age_valid(event.value)
            self.query_one("#btn-next", Button).disabled = not self._age_valid
            error = self.query_one("#age-error", Static)
            if event.value.strip() and not self._age_valid:
                error.update("[red]Enter a valid age or range (e.g. 10 or 8-12)[/red]")
            else:
                error.update("")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Advance step when Enter is pressed on the age input."""
        if event.input.id == "age-input" and self._validate_age():
            self._go_to_step(self._current_step + 1)

    # ── Validation & helpers ──────────────────────────────────────────────

    def _check_age_valid(self, value: str) -> bool:
        try:
            result = parse_str_age_range(value.strip())
        except ValueError:
            return False
        else:
            return result is not None

    def _validate_age(self) -> bool:
        age_input = self.query_one("#age-input", Input).value.strip()
        try:
            parsed = parse_str_age_range(age_input)
        except ValueError:
            parsed = None
        if parsed is None:
            self.query_one("#age-error", Static).update(
                "[red]Enter a valid age or range (e.g. 10 or 8-12)[/red]"
            )
            return False
        self._child_age_range = parsed
        self.query_one("#age-error", Static).update("")
        return True

    def _collect_weights(self) -> CategoryWeights:
        kwargs: dict[str, int] = {}
        # Query all WeightRow widgets and collect by field_name
        for row in self.query(WeightRow):
            kwargs[row.field_name] = row.value
        return CategoryWeights(**kwargs)

    def _finish(self) -> None:
        if not self._validate_age() or self._child_age_range is None:
            self._go_to_step(1)
            return

        weights = self._collect_weights()
        provider_select = cast(
            "Select[RatingProviderType]", self.query_one("#provider-select", Select)
        )
        api_key_str = self.query_one("#api-key-input", Input).value.strip()
        provider_val = provider_select.value
        provider = provider_val if isinstance(provider_val, RatingProviderType) else None
        api_key = TypeAdapter(SecretStr).validate_python(api_key_str) if api_key_str else None

        self.dismiss(
            OnboardingResult(
                child_age_range=self._child_age_range,
                weights=weights,
                provider=provider,
                api_key=api_key,
            )
        )

    def action_cancel(self) -> None:
        """Dismiss the screen (exits the app on first run)."""
        self.dismiss(None)
