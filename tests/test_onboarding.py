"""Unit and integration tests for the onboarding weight rows and setup wizard."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button, Input

from netflix_narc.main import NetflixNarcApp
from netflix_narc.manual_db import ManualMetadata
from netflix_narc.onboarding import (
    _WEIGHT_MAX,
    _WEIGHT_MIN,
    OnboardingScreen,
    WeightImpactPreview,
    WeightRow,
)

if TYPE_CHECKING:
    from netflix_narc.settings import Settings


class WeightRowTestApp(App[None]):
    """A dummy app to isolate and test the WeightRow composite widget."""

    def __init__(
        self,
        label: str,
        field_name: str,
        default: int,
        initial: int | None = None,
    ) -> None:
        super().__init__()
        self.label = label
        self.field_name = field_name
        self.default = default
        self.initial = initial
        self.last_changed_value: int | None = None

    @override
    def compose(self) -> ComposeResult:
        yield WeightRow(
            label=self.label,
            field_name=self.field_name,
            default=self.default,
            initial=self.initial,
        )

    def on_weight_row_changed(self, event: WeightRow.Changed) -> None:
        self.last_changed_value = event.value


@pytest.mark.asyncio
async def test_weight_row_initial_and_click() -> None:
    """Test that WeightRow displays initial values, handles button clicks, and fires events."""
    default_val = 4
    initial_val = 2
    new_val = 5

    app = WeightRowTestApp(
        "Violence & Scariness", "violence", default=default_val, initial=initial_val
    )
    async with app.run_test() as pilot:
        # Check initial state
        row = app.query_one(WeightRow)
        assert row.value == initial_val
        assert row.default == default_val

        # Verify buttons range from 1 to 5
        for w in range(_WEIGHT_MIN, _WEIGHT_MAX + 1):
            btn = app.query_one(f"#wr-violence-{w}", Button)
            assert btn is not None
            # The active button should have the primary variant
            if w == initial_val:
                assert btn.variant == "primary"
            else:
                assert btn.variant == "default"

        # Press a different weight button: 5 (V.High)
        await pilot.click(f"#wr-violence-{new_val}")
        await pilot.pause()

        assert row.value == new_val
        assert app.last_changed_value == new_val
        assert app.query_one(f"#wr-violence-{new_val}", Button).variant == "primary"
        assert app.query_one(f"#wr-violence-{initial_val}", Button).variant == "default"


@pytest.mark.asyncio
async def test_weight_row_reset() -> None:
    """Test that WeightRow resets to the specified default value when ↺ is clicked."""
    default_val = 4
    initial_val = 1

    app = WeightRowTestApp("Sexy Stuff", "sexy_stuff", default=default_val, initial=initial_val)
    async with app.run_test() as pilot:
        row = app.query_one(WeightRow)
        assert row.value == initial_val

        # Click the reset button
        await pilot.click("#wr-sexy_stuff-reset")
        await pilot.pause()

        # Should revert to default (4)
        assert row.value == default_val
        assert app.last_changed_value == default_val
        assert app.query_one(f"#wr-sexy_stuff-{default_val}", Button).variant == "primary"


@pytest.mark.asyncio
async def test_onboarding_screen_forwards_weight_changes(fake_settings: Settings) -> None:
    """Test that OnboardingScreen forwards WeightRow.Changed events to WeightImpactPreview."""
    # We need at least two manual records for WeightImpactPreview to display
    record1 = ManualMetadata(
        title="Show A",
        content_rating="PG",
        user_rating=8.0,
        category_scores={"Violence & Scariness": 4},
    )
    record2 = ManualMetadata(
        title="Show B",
        content_rating="G",
        user_rating=10.0,
        category_scores={"Violence & Scariness": 2},
    )

    app = NetflixNarcApp(settings=fake_settings, csv_path=None)
    await app.evidence_locker.upsert_record(record1)
    await app.evidence_locker.upsert_record(record2)

    async with app.run_test(size=(120, 60)) as pilot:
        await pilot.pause()
        await pilot.pause()  # let onboarding screen appear

        onb = next(s for s in pilot.app.screen_stack if isinstance(s, OnboardingScreen))

        # Step 1: Welcome. Click Next to go to Step 2
        await pilot.click("#btn-next")
        await pilot.pause()

        # Step 2: Age. Enter "10" and click Next
        onb.query_one("#age-input", Input).value = "10"
        await pilot.click("#btn-next")
        await pilot.pause()

        # Step 3: Weights.
        # Check that WeightImpactPreview is yielded
        preview = onb.query_one(WeightImpactPreview)
        assert preview is not None

        # Verify that the initial weights in the preview match the baseline settings weights
        assert preview._current_weights.violence == fake_settings.weights.violence  # noqa: SLF001

        # Click the "5" button in the Violence weight row
        new_val = 5
        await pilot.click(f"#wr-violence-{new_val}")
        await pilot.pause()

        # Verify that the preview's current weights reactively updated to 5!
        assert preview._current_weights.violence == new_val  # noqa: SLF001


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-vv"])
