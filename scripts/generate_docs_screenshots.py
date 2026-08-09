"""Script to programmatically capture high-resolution SVG TUI screenshots for documentation."""

from __future__ import annotations

import asyncio
import pathlib
import tempfile

from netflix_narc.main import NetflixNarcApp
from netflix_narc.manual_db import ManualMetadata
from netflix_narc.settings import Settings


async def generate_screenshots() -> None:
    """Capture SVG screenshots of all main Textual screens in netflix-narc."""
    assets_dir = pathlib.Path("docs/assets/images")
    assets_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_cache_dir = pathlib.Path(tmp_dir)

        # 1. Onboarding Screen
        print("Capturing onboarding screen...")
        settings_onb = Settings(child_age_range=None)
        app_onb = NetflixNarcApp(settings=settings_onb, csv_path=None, cache_dir=tmp_cache_dir)
        async with app_onb.run_test(size=(120, 36)) as pilot:
            await pilot.pause()
            await pilot.pause()
            svg_onb = app_onb.export_screenshot()
            (assets_dir / "onboarding_screen.svg").write_text(svg_onb)

        # 2. Main App (Lineup Screen, Interrogation Room, Preferences Screen)
        print("Capturing Lineup, Interrogation Room, and Preferences screens...")
        settings = Settings(child_age_range=(7, 12))
        app = NetflixNarcApp(settings=settings, csv_path=None, cache_dir=tmp_cache_dir)

        await app.evidence_locker.init()
        await app.evidence_locker.upsert_record(
            ManualMetadata(
                title="Stranger Things",
                content_rating="TV-14",
                user_rating=8.7,
                image_url="http://example.com/st.jpg",
                category_scores={
                    "Violence & Scariness": 4,
                    "Educational Value": 2,
                    "Positive Messages": 3,
                    "Positive Role Models": 3,
                    "Language": 3,
                    "Sexy Stuff": 2,
                },
            )
        )
        await app.evidence_locker.upsert_record(
            ManualMetadata(
                title="PAW Patrol: The Movie",
                content_rating="G",
                user_rating=6.1,
                image_url="http://example.com/paw.jpg",
                category_scores={
                    "Violence & Scariness": 1,
                    "Educational Value": 5,
                    "Positive Messages": 5,
                    "Positive Role Models": 5,
                    "Language": 1,
                    "Sexy Stuff": 1,
                },
            )
        )

        async with app.run_test(size=(120, 36)) as pilot:
            await pilot.pause()
            await pilot.pause()

            # Save Lineup Screen
            svg_lineup = app.export_screenshot()
            (assets_dir / "lineup_screen.svg").write_text(svg_lineup)

            # Save Interrogation Room
            await pilot.press("i")
            await pilot.pause()
            svg_interrogation = app.export_screenshot()
            (assets_dir / "interrogation_screen.svg").write_text(svg_interrogation)

            # Save Preferences Screen
            await pilot.press("s")
            await pilot.pause()
            svg_preferences = app.export_screenshot()
            (assets_dir / "preferences_screen.svg").write_text(svg_preferences)

        print("All screenshots generated successfully in docs/assets/images/")


if __name__ == "__main__":
    asyncio.run(generate_screenshots())
