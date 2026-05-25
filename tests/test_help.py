"""Async TUI tests for the HelpScreen and its integration.

Uses Textual's ``App.run_test()`` async context manager to drive the app
without a real terminal.
"""

from __future__ import annotations

import pytest
from pydantic import SecretStr
from textual.widgets import Button

from netflix_narc.help_screen import HelpScreen
from netflix_narc.main import NetflixNarcApp, SetupScreen
from netflix_narc.settings import Settings


@pytest.fixture()
def no_onboard_settings() -> Settings:
    """Settings configured with child_age_range so onboarding is skipped on mount."""
    return Settings(
        csm_api_key=SecretStr("fake-key"),
        omdb_api_key=SecretStr("fake-key"),
        tmdb_api_key=SecretStr("fake-key"),
        child_age_range=(8, 12),
        _env_file=None,  # type: ignore[call-arg]
    )


async def test_action_help_pushes_help_screen(no_onboard_settings: Settings) -> None:
    """Pressing 'h' should push a HelpScreen onto the screen stack."""
    app = NetflixNarcApp(settings=no_onboard_settings, csv_path=None)
    async with app.run_test() as pilot:
        await pilot.pause()

        # Verify SetupScreen is NOT on the stack
        assert not any(isinstance(s, SetupScreen) for s in pilot.app.screen_stack)

        # Now press 'h' to trigger help
        await pilot.press("h")
        await pilot.pause()

        screens_after = pilot.app.screen_stack
        assert any(isinstance(s, HelpScreen) for s in screens_after)


async def test_action_question_mark_pushes_help_screen(no_onboard_settings: Settings) -> None:
    """Pressing '?' should push a HelpScreen onto the screen stack."""
    app = NetflixNarcApp(settings=no_onboard_settings, csv_path=None)
    async with app.run_test() as pilot:
        await pilot.pause()

        # Press '?' to trigger help
        await pilot.press("?")
        await pilot.pause()

        screens_after = pilot.app.screen_stack
        assert any(isinstance(s, HelpScreen) for s in screens_after)


async def test_setup_screen_help_button_pushes_help_screen(no_onboard_settings: Settings) -> None:
    """Pressing the 'Help / About' button on SetupScreen pushes a HelpScreen."""
    app = NetflixNarcApp(settings=no_onboard_settings, csv_path=None)
    async with app.run_test() as pilot:
        await pilot.pause()

        # Push SetupScreen manually
        await pilot.press("s")
        await pilot.pause()

        # Trigger the help button on SetupScreen programmatically
        btn = pilot.app.screen.query_one("#btn-help", Button)
        btn.press()
        await pilot.pause()

        screens_after = pilot.app.screen_stack
        assert any(isinstance(s, HelpScreen) for s in screens_after)


async def test_help_screen_dismiss_pops_screen(no_onboard_settings: Settings) -> None:
    """Pressing escape on HelpScreen should dismiss it."""
    app = NetflixNarcApp(settings=no_onboard_settings, csv_path=None)
    async with app.run_test() as pilot:
        await pilot.pause()

        # Press 'h' to open HelpScreen
        await pilot.press("h")
        await pilot.pause()

        # Verify it is open
        assert any(isinstance(s, HelpScreen) for s in pilot.app.screen_stack)

        # Press escape to close it
        await pilot.press("escape")
        await pilot.pause()

        # Verify it is closed
        assert not any(isinstance(s, HelpScreen) for s in pilot.app.screen_stack)


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
