"""Script to programmatically capture high-resolution SVG TUI screenshots for documentation."""

from __future__ import annotations

import argparse
import asyncio
import os
import pathlib
import tempfile

from netflix_narc.main import NetflixNarcApp
from netflix_narc.sample_data import get_sample_manual_records
from netflix_narc.settings import Settings


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Capture high-resolution SVG TUI screenshots for documentation."
    )
    default_output_dir = pathlib.Path(os.environ.get("DOCS_SCREENSHOTS_DIR", "docs/assets/images"))
    parser.add_argument(
        "--output-dir",
        "-o",
        type=pathlib.Path,
        default=default_output_dir,
        help=(
            "Directory where generated SVG screenshots will be saved "
            "(default: docs/assets/images or $DOCS_SCREENSHOTS_DIR)"
        ),
    )
    return parser.parse_args()


async def generate_screenshots(output_dir: pathlib.Path) -> None:
    """Capture SVG screenshots of all main Textual screens in netflix-narc."""
    output_dir.mkdir(parents=True, exist_ok=True)

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
            (output_dir / "onboarding_screen.svg").write_text(svg_onb)

        # 2. Main App (Lineup Screen, Interrogation Room, Preferences Screen)
        print("Capturing Lineup, Interrogation Room, and Preferences screens...")
        settings = Settings(child_age_range=(7, 12))
        app = NetflixNarcApp(settings=settings, csv_path=None, cache_dir=tmp_cache_dir)

        await app.evidence_locker.init()
        for record in get_sample_manual_records():
            await app.evidence_locker.upsert_record(record)

        async with app.run_test(size=(120, 36)) as pilot:
            await pilot.pause()
            await pilot.pause()

            # Save Lineup Screen
            svg_lineup = app.export_screenshot()
            (output_dir / "lineup_screen.svg").write_text(svg_lineup)

            # Save Interrogation Room
            await pilot.press("i")
            await pilot.pause()
            svg_interrogation = app.export_screenshot()
            (output_dir / "interrogation_screen.svg").write_text(svg_interrogation)

            # Save Preferences Screen
            await pilot.press("s")
            await pilot.pause()
            svg_preferences = app.export_screenshot()
            (output_dir / "preferences_screen.svg").write_text(svg_preferences)

        print(f"All screenshots generated successfully in {output_dir}/")


def main() -> None:
    """Main entrypoint for script execution."""
    args = parse_args()
    asyncio.run(generate_screenshots(args.output_dir))


if __name__ == "__main__":
    main()
