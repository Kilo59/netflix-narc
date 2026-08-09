"""Unit and integration tests for the InterrogationRoomScreen manual entry UI."""

from __future__ import annotations

import pathlib
from typing import TYPE_CHECKING

import pytest
from textual.widgets import Checkbox, Input, Static

from netflix_narc.interrogation_room import InterrogationRoomScreen
from netflix_narc.main import NetflixNarcApp
from netflix_narc.manual_db import ManualMetadata

if TYPE_CHECKING:
    from netflix_narc.settings import Settings


@pytest.mark.asyncio
async def test_interrogation_room_mount_empty(
    fake_settings: Settings, tmp_path: pathlib.Path
) -> None:
    """Mounting InterrogationRoomScreen with no existing DB record initializes blank inputs."""
    fake_settings.child_age_range = (8, 12)
    app = NetflixNarcApp(settings=fake_settings, csv_path=None, cache_dir=tmp_path)
    screen = InterrogationRoomScreen("Unknown Title")

    async with app.run_test(size=(160, 200)) as pilot:
        await app.push_screen(screen)
        await pilot.pause()

        age_input = screen.query_one("#input-age-rating", Input)
        assert age_input.value == ""

        quality_input = screen.query_one("#input-quality-rating", Input)
        assert quality_input.value == ""

        flag_checkbox = screen.query_one("#input-flag", Checkbox)
        assert flag_checkbox.value is False

        overall_bar = screen.query_one("#overall-suitability-bar", Static)
        assert "Overall Suitability:" in str(overall_bar.render())


@pytest.mark.asyncio
async def test_interrogation_room_mount_existing_record(
    fake_settings: Settings, tmp_path: pathlib.Path
) -> None:
    """Mounting screen pre-fills form inputs from existing Evidence Locker record."""
    fake_settings.child_age_range = (8, 12)
    app = NetflixNarcApp(settings=fake_settings, csv_path=None, cache_dir=tmp_path)
    await app.evidence_locker.init()

    existing = ManualMetadata(
        title="Arcane",
        content_rating="TV-14",
        user_rating=4.0,
        image_url="http://example.com/cover.jpg",
        flagged_for_followup=True,
        category_scores={"Violence & Scariness": 4.0, "Sexy Stuff": 1.0},
    )
    await app.evidence_locker.upsert_record(existing)

    screen = InterrogationRoomScreen("Arcane")
    async with app.run_test(size=(160, 200)) as pilot:
        await app.push_screen(screen)
        await pilot.pause()

        assert screen.query_one("#input-age-rating", Input).value == "TV-14"
        assert screen.query_one("#input-quality-rating", Input).value == "4"
        assert screen.query_one("#input-image-url", Input).value == "http://example.com/cover.jpg"
        assert screen.query_one("#input-flag", Checkbox).value is True
        assert screen.query_one("#csm-VIOLENCE", Input).value == "4.0"
        assert screen.query_one("#csm-SEXY_STUFF", Input).value == "1.0"


@pytest.mark.asyncio
async def test_interrogation_room_realtime_suitability_updates(
    fake_settings: Settings, tmp_path: pathlib.Path
) -> None:
    """Typing into form inputs triggers real-time suitability recalculations."""
    fake_settings.child_age_range = (8, 12)
    app = NetflixNarcApp(settings=fake_settings, csv_path=None, cache_dir=tmp_path)
    screen = InterrogationRoomScreen("Stranger Things")

    async with app.run_test(size=(160, 200)) as pilot:
        await app.push_screen(screen)
        await pilot.pause()

        age_input = screen.query_one("#input-age-rating", Input)
        age_input.value = "16"
        await pilot.pause()

        overall_bar = screen.query_one("#overall-suitability-bar", Static)
        assert "Overall Suitability:" in str(overall_bar.render())

        quality_input = screen.query_one("#input-quality-rating", Input)
        quality_input.value = "5"
        await pilot.pause()

        csm_violence = screen.query_one("#csm-VIOLENCE", Input)
        csm_violence.value = "5"
        await pilot.pause()

        assert screen.query_one("#suitability-dashboard").tooltip is not None
        assert "Stranger Things" in str(screen.query_one("#suitability-dashboard").tooltip)


@pytest.mark.asyncio
async def test_interrogation_room_save_record(
    fake_settings: Settings, tmp_path: pathlib.Path
) -> None:
    """Submitting form via save button writes record to DB and dismisses screen."""
    fake_settings.child_age_range = (8, 12)
    app = NetflixNarcApp(settings=fake_settings, csv_path=None, cache_dir=tmp_path)
    await app.evidence_locker.init()

    screen = InterrogationRoomScreen("Squid Game")
    async with app.run_test(size=(160, 200)) as pilot:
        await app.push_screen(screen)
        await pilot.pause()

        screen.query_one("#input-age-rating", Input).value = "18"
        screen.query_one("#input-quality-rating", Input).value = "4.5"
        screen.query_one("#input-flag", Checkbox).value = True
        screen.query_one("#csm-VIOLENCE", Input).value = "5"

        await pilot.click("#btn-save")
        await pilot.pause()

        record = await app.evidence_locker.get_record("Squid Game")
        assert record is not None
        assert record.content_rating == "18"
        assert record.user_rating == 4.5
        assert record.flagged_for_followup is True
        assert record.category_scores.get("Violence & Scariness") == 5.0
        assert not any(isinstance(s, InterrogationRoomScreen) for s in app.screen_stack)


@pytest.mark.asyncio
async def test_interrogation_room_cancel_action(
    fake_settings: Settings, tmp_path: pathlib.Path
) -> None:
    """Clicking cancel button dismisses screen without modifying the database."""
    fake_settings.child_age_range = (8, 12)
    app = NetflixNarcApp(settings=fake_settings, csv_path=None, cache_dir=tmp_path)
    await app.evidence_locker.init()

    screen = InterrogationRoomScreen("Cancelled Show")
    async with app.run_test(size=(160, 200)) as pilot:
        await app.push_screen(screen)
        await pilot.pause()

        screen.query_one("#input-age-rating", Input).value = "12"
        await pilot.click("#btn-cancel")
        await pilot.pause()

        record = await app.evidence_locker.get_record("Cancelled Show")
        assert record is None
        assert not any(isinstance(s, InterrogationRoomScreen) for s in app.screen_stack)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("input_quality", "expected_clamped"),
    [
        ("10", 5.0),
        ("0", 1.0),
        ("-5", 1.0),
        ("3.5", 3.5),
    ],
)
async def test_interrogation_room_quality_rating_clamping(
    fake_settings: Settings,
    tmp_path: pathlib.Path,
    input_quality: str,
    expected_clamped: float,
) -> None:
    """Quality rating input values are clamped strictly within [1.0, 5.0]."""
    fake_settings.child_age_range = (8, 12)
    app = NetflixNarcApp(settings=fake_settings, csv_path=None, cache_dir=tmp_path)
    await app.evidence_locker.init()

    screen = InterrogationRoomScreen("Clamped Title")
    async with app.run_test(size=(160, 200)) as pilot:
        await app.push_screen(screen)
        await pilot.pause()

        screen.query_one("#input-quality-rating", Input).value = input_quality
        await pilot.click("#btn-save")
        await pilot.pause()

        record = await app.evidence_locker.get_record("Clamped Title")
        assert record is not None
        assert record.user_rating == expected_clamped


@pytest.mark.asyncio
async def test_interrogation_room_browser_search_and_paste_image(
    fake_settings: Settings, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Search web opens browser URL and paste image button handles clipboard failure gracefully."""
    fake_settings.child_age_range = (8, 12)
    app = NetflixNarcApp(settings=fake_settings, csv_path=None, cache_dir=tmp_path)

    opened_urls: list[str] = []
    monkeypatch.setattr("webbrowser.open", opened_urls.append)

    screen = InterrogationRoomScreen("The Matrix")

    async with app.run_test(size=(160, 200)) as pilot:
        await app.push_screen(screen)
        await pilot.pause()

        await pilot.click("#btn-search-web")
        await pilot.pause()
        assert len(opened_urls) == 1
        assert "The+Matrix" in opened_urls[0]

        # Test paste image button when clipboard has no image:
        # the image URL input should remain unchanged to prove graceful error handling.
        image_input = screen.query_one("#input-image-url", Input)
        original_image_url = image_input.value

        await pilot.click("#btn-paste-image")
        await pilot.pause()

        assert image_input.value == original_image_url


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
