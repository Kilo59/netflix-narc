"""Unit and integration tests for the onboarding weight rows and setup wizard."""

from __future__ import annotations

import pathlib
from typing import TYPE_CHECKING, override

import pytest
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Button, Input, Static

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
async def test_onboarding_screen_forwards_weight_changes(
    fake_settings: Settings, tmp_path: pathlib.Path
) -> None:
    """Test that OnboardingScreen forwards WeightRow.Changed events to WeightImpactPreview."""
    # We need at least two manual records for WeightImpactPreview to display
    record1 = ManualMetadata(
        title="Show A",
        content_rating="PG",
        user_rating=8.0,
        image_url="http://example.com/a.jpg",
        category_scores={
            "Violence & Scariness": 4,
            "Educational Value": 5,
            "Positive Messages": 4,
            "Positive Role Models": 4,
            "Language": 1,
        },
    )
    record2 = ManualMetadata(
        title="Show B",
        content_rating="G",
        user_rating=10.0,
        image_url="http://example.com/b.jpg",
        category_scores={
            "Violence & Scariness": 2,
            "Educational Value": 5,
            "Positive Messages": 5,
            "Positive Role Models": 5,
            "Language": 1,
        },
    )

    app = NetflixNarcApp(settings=fake_settings, csv_path=None, cache_dir=tmp_path)
    await app.evidence_locker.init()
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

        # Verify that the initial violence weight row value matches fake_settings
        violence_row = next(r for r in onb.query(WeightRow) if r.field_name == "violence")
        assert violence_row.value == fake_settings.weights.violence

        # Click the "5" button in the Violence weight row
        new_val = 5
        await pilot.click(f"#wr-violence-{new_val}")
        await pilot.pause()

        # Verify that the violence weight row value reactively updated to 5!
        assert violence_row.value == new_val


@pytest.mark.asyncio
async def test_onboarding_invalid_age_validation(
    fake_settings: Settings, tmp_path: pathlib.Path
) -> None:
    """Entering an invalid age should display an error message and block navigation."""
    app = NetflixNarcApp(settings=fake_settings, csv_path=None, cache_dir=tmp_path)
    async with app.run_test(size=(120, 60)) as pilot:
        await pilot.pause()
        await pilot.pause()

        onb = next(s for s in pilot.app.screen_stack if isinstance(s, OnboardingScreen))

        # Advance to step 1 (Age input)
        await pilot.click("#btn-next")
        await pilot.pause()

        # Enter invalid age string
        age_input = onb.query_one("#age-input", Input)
        age_input.value = "invalid_age_str"
        await pilot.click("#btn-next")
        await pilot.pause()

        # Verify error text is displayed and step remains 1
        error_widget = onb.query_one("#age-error", Static)
        assert error_widget.has_class("hidden") is False
        assert "Enter a valid age" in str(error_widget.content)

        assert onb.query_one("#step-age", Container).has_class("hidden") is False


@pytest.mark.asyncio
async def test_onboarding_navigation_back_and_skip(
    fake_settings: Settings, tmp_path: pathlib.Path
) -> None:
    """Test navigating backwards with btn-back and skipping optional steps with btn-skip."""
    app = NetflixNarcApp(settings=fake_settings, csv_path=None, cache_dir=tmp_path)
    async with app.run_test(size=(120, 60)) as pilot:
        await pilot.pause()
        await pilot.pause()

        onb = next(s for s in pilot.app.screen_stack if isinstance(s, OnboardingScreen))
        assert onb.query_one("#step-welcome", Container).has_class("hidden") is False

        # Step 0 -> Step 1
        await pilot.click("#btn-next")
        await pilot.pause()
        assert onb.query_one("#step-age", Container).has_class("hidden") is False

        # Step 1 -> Step 0 via Back
        await pilot.click("#btn-back")
        await pilot.pause()
        assert onb.query_one("#step-welcome", Container).has_class("hidden") is False

        # Step 0 -> Step 1 -> valid age -> Step 2
        await pilot.click("#btn-next")
        await pilot.pause()
        age_input = onb.query_one("#age-input", Input)
        age_input.value = "10"
        age_input.post_message(Input.Changed(age_input, "10"))
        await pilot.pause()
        await pilot.click("#btn-next")
        await pilot.pause()
        assert onb.query_one("#step-weights", Container).has_class("hidden") is False

        # Step 2 (Weights - optional) -> Skip -> Step 3 (API)
        skip_btn = onb.query_one("#btn-skip", Button)
        skip_btn.press()
        await pilot.pause()
        assert onb.query_one("#step-api", Container).has_class("hidden") is False

        # Step 3 (API - optional) -> Skip -> Step 4 (Summary)
        skip_btn.press()
        await pilot.pause()
        assert onb.query_one("#step-summary", Container).has_class("hidden") is False


@pytest.mark.asyncio
async def test_onboarding_reset_all_weights_button(
    fake_settings: Settings, tmp_path: pathlib.Path
) -> None:
    """Clicking btn-reset-all-weights resets all WeightRow values to default."""
    app = NetflixNarcApp(settings=fake_settings, csv_path=None, cache_dir=tmp_path)
    async with app.run_test(size=(120, 60)) as pilot:
        await pilot.pause()
        await pilot.pause()

        onb = next(s for s in pilot.app.screen_stack if isinstance(s, OnboardingScreen))

        # Advance to step 2 (Weights)
        await pilot.click("#btn-next")
        await pilot.pause()
        onb.query_one("#age-input", Input).value = "10"
        await pilot.click("#btn-next")
        await pilot.pause()

        # Modify a weight row
        await pilot.click("#wr-violence-1")
        await pilot.pause()

        # Click reset all weights button
        await pilot.click("#btn-reset-all-weights")
        await pilot.pause()

        # Check violence weight is reset to default (4)
        violence_row = next(r for r in onb.query(WeightRow) if r.field_name == "violence")
        assert violence_row.value == 4


@pytest.mark.asyncio
async def test_onboarding_public_api_helpers(
    fake_settings: Settings, tmp_path: pathlib.Path
) -> None:
    """go_to_step and set_child_age_range public methods drive wizard navigation cleanly."""
    app = NetflixNarcApp(settings=fake_settings, csv_path=None, cache_dir=tmp_path)
    async with app.run_test(size=(120, 60)) as pilot:
        await pilot.pause()

        onb = next(s for s in pilot.app.screen_stack if isinstance(s, OnboardingScreen))

        onb.set_child_age_range((8, 12))
        onb.go_to_step(2)
        await pilot.pause()

        assert onb.current_step == 2
        assert onb.child_age_range == (8, 12)
        assert onb.is_age_valid is True

        onb.go_to_step(3)
        await pilot.pause()
        assert onb.current_step == 3


@pytest.mark.asyncio
async def test_onboarding_public_api_single_age_helper(
    fake_settings: Settings, tmp_path: pathlib.Path
) -> None:
    """set_child_age_range formats single ages cleanly and marks age as valid."""
    app = NetflixNarcApp(settings=fake_settings, csv_path=None, cache_dir=tmp_path)
    async with app.run_test(size=(120, 60)) as pilot:
        await pilot.pause()

        onb = next(s for s in pilot.app.screen_stack if isinstance(s, OnboardingScreen))

        onb.set_child_age_range((10, 10))
        await pilot.pause()

        assert onb.child_age_range == (10, 10)
        assert onb.is_age_valid is True
        assert onb.child_age_input.value == "10"


def test_set_child_age_range_unmounted_warning() -> None:
    """Calling set_child_age_range on an unmounted OnboardingScreen issues UserWarning."""
    onb = OnboardingScreen()
    with pytest.warns(UserWarning, match=r"Failed to locate age input widget"):
        onb.set_child_age_range((8, 12))

    assert onb.child_age_range == (8, 12)
    assert onb.is_age_valid is True


@pytest.mark.asyncio
async def test_set_child_age_range_update_error_warning(
    fake_settings: Settings, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Failed age input value assignment issues UserWarning."""
    app = NetflixNarcApp(settings=fake_settings, csv_path=None, cache_dir=tmp_path)
    async with app.run_test(size=(120, 60)) as pilot:
        await pilot.pause()

        onb = next(s for s in pilot.app.screen_stack if isinstance(s, OnboardingScreen))

        def failing_set_value(*_args: object, **_kwargs: object) -> None:
            msg = "Mocked value assignment error"
            raise ValueError(msg)

        monkeypatch.setattr(
            Input, "value", property(fget=lambda *_args: "", fset=failing_set_value)
        )

        with pytest.warns(UserWarning, match=r"Failed to update age input value"):
            onb.set_child_age_range((8, 12))


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
