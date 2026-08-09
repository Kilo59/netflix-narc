"""Async TUI smoke tests for the NetflixNarcApp.

Uses Textual's ``App.run_test()`` async context manager to drive the app
without a real terminal. No real HTTP calls or filesystem writes are made.

Test strategy:
- ``fake_settings`` provides hermetic settings (no real .env).
- ``csv_path=None`` means no CSV is auto-loaded, so the table starts empty.
- Tests assert structural properties (widget presence, screen transitions).
- ``pytest-asyncio`` with ``asyncio_mode = "auto"`` handles async tests
  automatically (configured in ``pyproject.toml``).
"""

from __future__ import annotations

import datetime as dt
import pathlib

import pytest
from pydantic import SecretStr
from textual.coordinate import Coordinate
from textual.widgets import DataTable

from netflix_narc.help_screen import HelpScreen
from netflix_narc.interrogation_room import InterrogationRoomScreen
from netflix_narc.lineup import LineupScreen
from netflix_narc.main import (
    AdvancedScreen,
    LoadCsvScreen,
    NetflixNarcApp,
    SetupConfig,
    apply_setup_config,
    create_storage_backend,
)
from netflix_narc.onboarding import OnboardingScreen
from netflix_narc.parser import ViewingRecord
from netflix_narc.preferences import PreferencesScreen
from netflix_narc.settings import RatingProviderType, Settings, SyncBackendType
from netflix_narc.sync.local_folder import LocalStorageBackend
from netflix_narc.sync.s3 import S3StorageBackend
from netflix_narc.sync.webdav import WebDAVStorageBackend


async def test_app_mounts_without_crashing(tmp_path: pathlib.Path) -> None:
    """App should mount cleanly with no CSV path and no API keys configured.

    When child_age_range is None, on_mount pushes OnboardingScreen automatically.
    We verify the app doesn't crash and retains a DataTable in the DOM.
    """
    no_key_settings = Settings(
        csm_api_key=SecretStr(""),
        omdb_api_key=SecretStr(""),
        tmdb_api_key=SecretStr(""),
        _env_file=None,  # type: ignore[call-arg]
    )
    app = NetflixNarcApp(settings=no_key_settings, csv_path=None, cache_dir=tmp_path)
    async with app.run_test() as pilot:
        assert pilot.app.query(DataTable)


async def test_app_table_is_visible(fake_settings: Settings, tmp_path: pathlib.Path) -> None:
    """DataTable widget is present and queryable when the app mounts."""
    app = NetflixNarcApp(settings=fake_settings, csv_path=None, cache_dir=tmp_path)
    async with app.run_test() as pilot:
        table = pilot.app.query_one(DataTable)
        assert table is not None


async def test_action_settings_pushes_preferences_screen(
    fake_settings: Settings, tmp_path: pathlib.Path
) -> None:
    """Pressing 's' should push a PreferencesScreen onto the screen stack."""
    # Provide a child_age_range so onboarding is skipped
    fake_settings.child_age_range = (8, 12)
    app = NetflixNarcApp(settings=fake_settings, csv_path=None, cache_dir=tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("s")
        await pilot.pause()

        screens_after = pilot.app.screen_stack
        assert any(isinstance(s, PreferencesScreen) for s in screens_after)


async def test_preferences_screen_escape_pops_screen(
    fake_settings: Settings, tmp_path: pathlib.Path
) -> None:
    """Pressing Escape on PreferencesScreen should dismiss it and return to main app."""
    fake_settings.child_age_range = (8, 12)
    app = NetflixNarcApp(settings=fake_settings, csv_path=None, cache_dir=tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("s")
        await pilot.pause()

        # Escape should dismiss it
        await pilot.press("escape")
        await pilot.pause()

        screens_after = pilot.app.screen_stack
        assert not any(isinstance(s, PreferencesScreen) for s in screens_after)


async def test_onboarding_pushed_when_age_missing(tmp_path: pathlib.Path) -> None:
    """OnboardingScreen should appear when child_age_range is None."""
    no_age_settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
    )
    app = NetflixNarcApp(settings=no_age_settings, csv_path=None, cache_dir=tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()  # let call_after_refresh + async _push_onboarding run
        screens = pilot.app.screen_stack
        assert any(isinstance(s, OnboardingScreen) for s in screens)


async def test_preferences_screen_relaunch_button_pushes_onboarding_screen(
    fake_settings: Settings, tmp_path: pathlib.Path
) -> None:
    """Clicking 'Re-launch Setup Wizard' in PreferencesScreen should open OnboardingScreen."""
    fake_settings.child_age_range = (8, 12)
    app = NetflixNarcApp(settings=fake_settings, csv_path=None, cache_dir=tmp_path)
    async with app.run_test(size=(120, 140)) as pilot:
        await pilot.pause()
        await pilot.press("s")
        await pilot.pause()

        assert any(isinstance(s, PreferencesScreen) for s in pilot.app.screen_stack)

        await pilot.click("#pref-relaunch")
        await pilot.pause()
        await pilot.pause()

        assert any(isinstance(s, OnboardingScreen) for s in pilot.app.screen_stack)


async def test_action_show_help_pushes_help_screen(
    fake_settings: Settings, tmp_path: pathlib.Path
) -> None:
    """Pressing '?' or 'h' should push HelpScreen onto screen stack."""
    fake_settings.child_age_range = (8, 12)
    app = NetflixNarcApp(settings=fake_settings, csv_path=None, cache_dir=tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("?")
        await pilot.pause()

        assert any(isinstance(s, HelpScreen) for s in pilot.app.screen_stack)


async def test_action_start_lineup_pushes_lineup_screen(
    fake_settings: Settings, tmp_path: pathlib.Path
) -> None:
    """Pressing 'l' with items in queue should launch LineupScreen."""
    fake_settings.child_age_range = (8, 12)
    app = NetflixNarcApp(settings=fake_settings, csv_path=None, cache_dir=tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.grouped_records["Test Title"] = []
        await pilot.press("l")
        await pilot.pause()

        assert any(isinstance(s, LineupScreen) for s in pilot.app.screen_stack)


async def test_action_advanced_pushes_advanced_screen(
    fake_settings: Settings, tmp_path: pathlib.Path
) -> None:
    """Pressing 'a' should launch AdvancedScreen modal."""
    fake_settings.child_age_range = (8, 12)
    app = NetflixNarcApp(settings=fake_settings, csv_path=None, cache_dir=tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("a")
        await pilot.pause()

        assert any(isinstance(s, AdvancedScreen) for s in pilot.app.screen_stack)


async def test_advanced_screen_close_button(
    fake_settings: Settings, tmp_path: pathlib.Path
) -> None:
    """Clicking close in AdvancedScreen dismisses the modal."""
    fake_settings.child_age_range = (8, 12)
    app = NetflixNarcApp(settings=fake_settings, csv_path=None, cache_dir=tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("a")
        await pilot.pause()

        await pilot.click("#adv-close")
        await pilot.pause()

        assert not any(isinstance(s, AdvancedScreen) for s in pilot.app.screen_stack)


async def test_load_csv_screen_cancel_action(
    fake_settings: Settings, tmp_path: pathlib.Path
) -> None:
    """LoadCsvScreen cancel button dismisses screen."""
    fake_settings.child_age_range = (8, 12)
    app = NetflixNarcApp(settings=fake_settings, csv_path=None, cache_dir=tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()

        screen = LoadCsvScreen(current_path=tmp_path / "ViewingHistory.csv")
        await app.push_screen(screen)
        await pilot.pause()

        await pilot.click("#cancel-btn")
        await pilot.pause()

        assert not any(isinstance(s, LoadCsvScreen) for s in app.screen_stack)


@pytest.mark.parametrize(
    ("backend_type", "kwargs", "expected_type"),
    [
        (SyncBackendType.OFF, {}, type(None)),
        (SyncBackendType.LOCAL_FOLDER, {"sync_local_path": "sync/folder"}, LocalStorageBackend),
        (SyncBackendType.LOCAL_FOLDER, {"sync_local_path": ""}, LocalStorageBackend),
        (
            SyncBackendType.S3,
            {
                "sync_s3_endpoint_url": "https://s3.example.com",
                "sync_s3_bucket": "mybucket",
            },
            S3StorageBackend,
        ),
        (
            SyncBackendType.S3,
            {"sync_s3_endpoint_url": "", "sync_s3_bucket": "mybucket"},
            type(None),
        ),
        (
            SyncBackendType.WEBDAV,
            {
                "sync_webdav_url": "https://dav.example.com",
                "sync_webdav_username": "user",
            },
            WebDAVStorageBackend,
        ),
        (
            SyncBackendType.WEBDAV,
            {"sync_webdav_url": "", "sync_webdav_username": "user"},
            type(None),
        ),
    ],
)
def test_create_storage_backend(
    fake_settings: Settings,
    backend_type: SyncBackendType,
    kwargs: dict[str, str],
    expected_type: type | type[None],
) -> None:
    """create_storage_backend returns correct backend instance or None based on config."""
    fake_settings.sync_backend = backend_type
    for key, val in kwargs.items():
        setattr(fake_settings, key, val)

    backend = create_storage_backend(fake_settings)
    if expected_type is type(None):
        assert backend is None
    else:
        assert isinstance(backend, expected_type)


@pytest.mark.parametrize(
    "provider",
    [RatingProviderType.CSM, RatingProviderType.OMDB, RatingProviderType.TMDB],
)
def test_apply_setup_config(fake_settings: Settings, provider: RatingProviderType) -> None:
    """apply_setup_config updates in-memory settings and returns proper env dict."""
    config = SetupConfig(
        provider=provider,
        api_key=SecretStr("key123"),
        sync_backend=SyncBackendType.LOCAL_FOLDER,
        sync_local_path="/sync/path",
    )
    env = apply_setup_config(fake_settings, config)

    assert fake_settings.active_rating_provider == provider
    assert fake_settings.sync_backend == SyncBackendType.LOCAL_FOLDER
    assert fake_settings.sync_local_path == "/sync/path"
    assert env["SYNC_BACKEND"] == "local_folder"
    assert env["SYNC_LOCAL_PATH"] == "/sync/path"

    match provider:
        case RatingProviderType.CSM:
            assert fake_settings.csm_api_key.get_secret_value() == "key123"
        case RatingProviderType.OMDB:
            assert fake_settings.omdb_api_key.get_secret_value() == "key123"
        case RatingProviderType.TMDB:
            assert fake_settings.tmdb_api_key.get_secret_value() == "key123"


async def test_rebuild_table_expanded_titles(
    fake_settings: Settings, tmp_path: pathlib.Path
) -> None:
    """rebuild_table should render child viewing records when a title is expanded."""
    fake_settings.child_age_range = (8, 12)
    app = NetflixNarcApp(settings=fake_settings, csv_path=None, cache_dir=tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()

        record = ViewingRecord(
            title="Stranger Things: Season 1: Chapter One",
            date_watched=dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
        )
        app.grouped_records.clear()
        app.grouped_records["Stranger Things"] = [record]
        app.expanded_titles.add("Stranger Things")

        await app.rebuild_table(evaluate=False)
        await pilot.pause()

        table = app.query_one(DataTable)
        # Table should have parent row + child row
        assert table.row_count >= 2


async def test_action_interrogate_child_row_resolution(
    fake_settings: Settings, tmp_path: pathlib.Path
) -> None:
    """action_interrogate correctly maps child row keys back to base titles."""
    fake_settings.child_age_range = (8, 12)
    app = NetflixNarcApp(settings=fake_settings, csv_path=None, cache_dir=tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()

        record = ViewingRecord(
            title="Stranger Things: Season 1: Chapter One",
            date_watched=dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
        )
        app.grouped_records.clear()
        app.grouped_records["Stranger Things"] = [record]
        app.expanded_titles.add("Stranger Things")

        await app.rebuild_table(evaluate=False)
        await pilot.pause()

        table = app.query_one(DataTable)
        # Move cursor to child row
        table.cursor_coordinate = Coordinate(1, 0)
        app.action_interrogate()

        await pilot.pause()

        # InterrogationRoomScreen should be on top for base title
        top_screen = app.screen_stack[-1]
        assert isinstance(top_screen, InterrogationRoomScreen)
        assert top_screen.base_title == "Stranger Things"


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
