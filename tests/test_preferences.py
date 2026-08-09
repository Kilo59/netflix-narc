"""Unit and integration tests for the PreferencesScreen settings UI."""

from __future__ import annotations

import pathlib
from typing import TYPE_CHECKING

import pytest
from textual.widgets import Input, Select, Static

from netflix_narc.main import NetflixNarcApp
from netflix_narc.onboarding import WeightRow
from netflix_narc.preferences import PreferencesScreen
from netflix_narc.settings import ScoringMode

if TYPE_CHECKING:
    from netflix_narc.settings import Settings


@pytest.mark.asyncio
async def test_preferences_mount_and_initial_state(
    fake_settings: Settings, tmp_path: pathlib.Path
) -> None:
    """Mounting PreferencesScreen pre-fills input fields with current settings."""
    fake_settings.child_age_range = (8, 12)
    app = NetflixNarcApp(settings=fake_settings, csv_path=None, cache_dir=tmp_path)
    screen = PreferencesScreen(settings=fake_settings)

    async with app.run_test(size=(160, 200)) as pilot:
        await app.push_screen(screen)
        await pilot.pause()

        age_input = screen.query_one("#pref-age-input", Input)
        assert age_input.value == "8-12"

        title = screen.query_one("#prefs-title", Static)
        assert "PREFERENCES" in str(title.render())


@pytest.mark.asyncio
async def test_preferences_scoring_mode_description_update(
    fake_settings: Settings, tmp_path: pathlib.Path
) -> None:
    """Changing scoring mode dropdown dynamically updates description text."""
    fake_settings.child_age_range = (8, 12)
    app = NetflixNarcApp(settings=fake_settings, csv_path=None, cache_dir=tmp_path)
    screen = PreferencesScreen(settings=fake_settings)

    async with app.run_test(size=(160, 200)) as pilot:
        await app.push_screen(screen)
        await pilot.pause()

        scoring_select = screen.query_one("#pref-scoring-mode-select", Select)
        scoring_select.value = ScoringMode.QUALITY_FOCUS
        await pilot.pause()

        desc = screen.query_one("#pref-scoring-mode-description", Static)
        assert "Quality Focus" in str(desc.render()) or "Option A" in str(desc.render())


@pytest.mark.asyncio
async def test_preferences_reset_weights(fake_settings: Settings, tmp_path: pathlib.Path) -> None:
    """Clicking Reset Weights resets all WeightRow instances to default values."""
    fake_settings.child_age_range = (8, 12)
    app = NetflixNarcApp(settings=fake_settings, csv_path=None, cache_dir=tmp_path)
    screen = PreferencesScreen(settings=fake_settings)

    async with app.run_test(size=(160, 200)) as pilot:
        await app.push_screen(screen)
        await pilot.pause()

        first_row = screen.query(WeightRow).first()
        first_row.value = 1
        await pilot.pause()

        await pilot.click("#pref-reset-weights")
        await pilot.pause()

        assert first_row.value == first_row.default


@pytest.mark.asyncio
async def test_preferences_save_updates_settings(
    fake_settings: Settings, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Valid form submission updates in-memory settings and dismisses preferences screen."""
    fake_settings.child_age_range = (8, 12)
    app = NetflixNarcApp(settings=fake_settings, csv_path=None, cache_dir=tmp_path)
    screen = PreferencesScreen(settings=fake_settings)

    saved_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        "netflix_narc.persistence.update_env_file",
        lambda **kwargs: saved_calls.append(kwargs),
    )

    async with app.run_test(size=(160, 200)) as pilot:
        await app.push_screen(screen)
        await pilot.pause()

        screen.query_one("#pref-age-input", Input).value = "10-14"
        await pilot.click("#pref-save")
        await pilot.pause()

        assert len(saved_calls) == 1
        assert fake_settings.child_age_range == (10, 14)
        assert not any(isinstance(s, PreferencesScreen) for s in app.screen_stack)


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_age", ["abc", "invalid", "no-digits"])
async def test_preferences_invalid_age_shows_error(
    fake_settings: Settings, tmp_path: pathlib.Path, invalid_age: str
) -> None:
    """Entering an invalid age range shows error message and halts save operation."""
    fake_settings.child_age_range = (8, 12)
    app = NetflixNarcApp(settings=fake_settings, csv_path=None, cache_dir=tmp_path)
    screen = PreferencesScreen(settings=fake_settings)

    async with app.run_test(size=(160, 200)) as pilot:
        await app.push_screen(screen)
        await pilot.pause()

        screen.query_one("#pref-age-input", Input).value = invalid_age
        await pilot.click("#pref-save")
        await pilot.pause()

        err_static = screen.query_one("#pref-age-error", Static)
        assert err_static.has_class("hidden") is False
        assert "Invalid age range" in str(err_static.render())
        assert any(isinstance(s, PreferencesScreen) for s in app.screen_stack)


@pytest.mark.asyncio
async def test_preferences_dismiss_via_close_button(
    fake_settings: Settings, tmp_path: pathlib.Path
) -> None:
    """Clicking close button dismisses preferences without saving."""
    fake_settings.child_age_range = (8, 12)
    app = NetflixNarcApp(settings=fake_settings, csv_path=None, cache_dir=tmp_path)
    screen = PreferencesScreen(settings=fake_settings)

    async with app.run_test(size=(160, 200)) as pilot:
        await app.push_screen(screen)
        await pilot.pause()

        await pilot.click("#pref-close")
        await pilot.pause()

        assert not any(isinstance(s, PreferencesScreen) for s in app.screen_stack)


@pytest.mark.asyncio
async def test_preferences_dismiss_via_escape_key(
    fake_settings: Settings, tmp_path: pathlib.Path
) -> None:
    """Pressing escape key dismisses preferences without saving."""
    fake_settings.child_age_range = (8, 12)
    app = NetflixNarcApp(settings=fake_settings, csv_path=None, cache_dir=tmp_path)
    screen = PreferencesScreen(settings=fake_settings)

    async with app.run_test(size=(160, 200)) as pilot:
        await app.push_screen(screen)
        await pilot.pause()

        await pilot.press("escape")
        await pilot.pause()

        assert not any(isinstance(s, PreferencesScreen) for s in app.screen_stack)


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
