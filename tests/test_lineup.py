"""Unit and integration tests for the LineupScreen queue discovery UI."""

from __future__ import annotations

import datetime as dt
import pathlib
from typing import TYPE_CHECKING

import pytest
from textual.widgets import Static

from netflix_narc.interrogation_room import InterrogationRoomScreen
from netflix_narc.lineup import LineupScreen
from netflix_narc.main import NetflixNarcApp
from netflix_narc.parser import ViewingRecord

if TYPE_CHECKING:
    from netflix_narc.settings import Settings


@pytest.mark.asyncio
async def test_lineup_mount_and_ui_rendering(
    fake_settings: Settings, tmp_path: pathlib.Path
) -> None:
    """Mounting LineupScreen renders title counter, dossier completeness,
    and viewing history info.
    """

    fake_settings.child_age_range = (8, 12)
    app = NetflixNarcApp(settings=fake_settings, csv_path=None, cache_dir=tmp_path)

    queue = ["Stranger Things", "Wednesday"]
    grouped_records = {
        "Stranger Things": [
            ViewingRecord(
                title="Stranger Things: Season 1: Chapter One",
                date_watched=dt.datetime(2023, 1, 15, tzinfo=dt.UTC),
            )
        ]
    }
    completeness_map = {"Stranger Things": 80}

    screen = LineupScreen(
        queue=queue, grouped_records=grouped_records, completeness_map=completeness_map
    )

    async with app.run_test() as pilot:
        await app.push_screen(screen)
        await pilot.pause()

        counter = screen.query_one("#lineup-counter", Static)
        assert "Title 1 of 2" in str(counter.content)

        title_info = screen.query_one("#title-info", Static)
        rendered_text = str(title_info.content)
        assert "Stranger Things" in rendered_text
        assert "2023-01-15" in rendered_text
        assert "80%" in rendered_text


@pytest.mark.asyncio
async def test_lineup_skip_action(fake_settings: Settings, tmp_path: pathlib.Path) -> None:
    """Pressing skip or clicking Skip advances the queue index without modifying database."""
    fake_settings.child_age_range = (8, 12)
    app = NetflixNarcApp(settings=fake_settings, csv_path=None, cache_dir=tmp_path)

    screen = LineupScreen(queue=["Movie A", "Movie B"])

    async with app.run_test() as pilot:
        await app.push_screen(screen)
        await pilot.pause()

        await pilot.click("#btn-skip")
        await pilot.pause()

        counter = screen.query_one("#lineup-counter", Static)
        assert "Title 2 of 2" in str(counter.content)


@pytest.mark.asyncio
async def test_lineup_ignore_action(fake_settings: Settings, tmp_path: pathlib.Path) -> None:
    """Clicking ignore marks title ignored in Evidence Locker and advances to next item."""
    fake_settings.child_age_range = (8, 12)
    app = NetflixNarcApp(settings=fake_settings, csv_path=None, cache_dir=tmp_path)
    await app.evidence_locker.init()

    screen = LineupScreen(queue=["Ignored Show", "Next Show"])

    async with app.run_test() as pilot:
        await app.push_screen(screen)
        await pilot.pause()

        await pilot.click("#btn-ignore")
        await pilot.pause()

        record = await app.evidence_locker.get_record("Ignored Show")
        assert record is not None
        assert record.ignored is True

        counter = screen.query_one("#lineup-counter", Static)
        assert "Title 2 of 2" in str(counter.content)


@pytest.mark.asyncio
async def test_lineup_interrogate_action(fake_settings: Settings, tmp_path: pathlib.Path) -> None:
    """Clicking Interrogate pushes InterrogationRoomScreen onto screen stack."""
    fake_settings.child_age_range = (8, 12)
    app = NetflixNarcApp(settings=fake_settings, csv_path=None, cache_dir=tmp_path)

    screen = LineupScreen(queue=["Interrogated Show"])

    async with app.run_test() as pilot:
        await app.push_screen(screen)
        await pilot.pause()

        await pilot.click("#btn-interrogate")
        await pilot.pause()

        assert any(isinstance(s, InterrogationRoomScreen) for s in app.screen_stack)


@pytest.mark.asyncio
async def test_lineup_empty_queue_pops(fake_settings: Settings, tmp_path: pathlib.Path) -> None:
    """When lineup queue is exhausted, screen automatically pops from screen stack."""
    fake_settings.child_age_range = (8, 12)
    app = NetflixNarcApp(settings=fake_settings, csv_path=None, cache_dir=tmp_path)

    screen = LineupScreen(queue=["Sole Show"])

    async with app.run_test() as pilot:
        await app.push_screen(screen)
        await pilot.pause()

        await pilot.click("#btn-skip")
        await pilot.pause()

        assert not any(isinstance(s, LineupScreen) for s in app.screen_stack)


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
