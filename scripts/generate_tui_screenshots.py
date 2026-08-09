"""Script to programmatically capture high-resolution SVG TUI screenshots for documentation."""

from __future__ import annotations

import argparse
import asyncio
import os
import pathlib
import tempfile
from typing import TYPE_CHECKING

from netflix_narc.main import NetflixNarcApp
from netflix_narc.onboarding import OnboardingScreen
from netflix_narc.sample_data import get_sample_manual_records
from netflix_narc.settings import Settings

if TYPE_CHECKING:
    from netflix_narc.manual_db import ManualMetadata


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


async def _capture_onboarding_screenshots(
    output_dir: pathlib.Path,
    records: list[ManualMetadata],
    tmp_cache_dir: pathlib.Path,
) -> None:
    """Capture Onboarding wizard steps 1, 2, and 3."""
    print("Capturing Onboarding wizard steps...")
    settings_onb = Settings(child_age_range=None)
    app_onb = NetflixNarcApp(settings=settings_onb, csv_path=None, cache_dir=tmp_cache_dir)

    await app_onb.evidence_locker.init()
    for record in records:
        await app_onb.evidence_locker.upsert_record(record)

    async with app_onb.run_test(size=(120, 42)) as pilot:
        await pilot.pause(0.5)

        onb_screen = app_onb.screen
        if isinstance(onb_screen, OnboardingScreen):
            # Step 1: Welcome & Profile
            svg_onb1 = app_onb.export_screenshot()
            (output_dir / "onboarding_step1.svg").write_text(svg_onb1)
            (output_dir / "onboarding_screen.svg").write_text(svg_onb1)

            # Step 2: Content Weights with Weight Impact Preview
            onb_screen._child_age_range = (8, 12)  # noqa: SLF001
            onb_screen._age_valid = True  # noqa: SLF001
            onb_screen._preview_records = records  # noqa: SLF001
            onb_screen._all_eligible = records  # noqa: SLF001
            onb_screen._go_to_step(2)  # noqa: SLF001
            await pilot.pause(0.5)

            svg_onb2 = app_onb.export_screenshot()
            (output_dir / "onboarding_step2.svg").write_text(svg_onb2)

            # Step 3: API Provider
            onb_screen._go_to_step(3)  # noqa: SLF001
            await pilot.pause(0.5)
            svg_onb3 = app_onb.export_screenshot()
            (output_dir / "onboarding_step3.svg").write_text(svg_onb3)


async def _capture_main_app_screenshots(
    output_dir: pathlib.Path,
    records: list[ManualMetadata],
    tmp_cache_dir: pathlib.Path,
    sample_csv: pathlib.Path | None,
) -> None:
    """Capture Lineup, DataTable, Interrogation, Preferences, Help, and Advanced screens."""
    print("Capturing main application screens...")
    settings = Settings(child_age_range=(7, 12))
    app = NetflixNarcApp(settings=settings, csv_path=None, cache_dir=tmp_cache_dir)

    await app.evidence_locker.init()
    for record in records:
        await app.evidence_locker.upsert_record(record)

    async with app.run_test(size=(120, 42)) as pilot:
        if sample_csv and sample_csv.exists():
            await app.load_data(str(sample_csv))
            await pilot.pause(0.5)

        # Lineup Screen (Card-based view)
        await pilot.press("l")
        await pilot.pause(0.5)
        svg_lineup = app.export_screenshot()
        (output_dir / "lineup_screen.svg").write_text(svg_lineup)
        await pilot.press("escape")
        await pilot.pause(0.3)

        # Main DataTable with Expanded Row showing Sub-bars
        await pilot.press("enter")  # Toggle row expansion
        await pilot.pause(0.3)
        svg_datatable = app.export_screenshot()
        (output_dir / "datatable_expanded.svg").write_text(svg_datatable)

        # Interrogation Room Screen
        await pilot.press("i")
        await pilot.pause(0.5)
        svg_interrogation = app.export_screenshot()
        (output_dir / "interrogation_screen.svg").write_text(svg_interrogation)
        await pilot.press("escape")
        await pilot.pause(0.3)

        # Preferences Screen
        await pilot.press("s")
        await pilot.pause(0.5)
        svg_preferences = app.export_screenshot()
        (output_dir / "preferences_screen.svg").write_text(svg_preferences)
        await pilot.press("escape")
        await pilot.pause(0.3)

        # Help Screen
        await pilot.press("h")
        await pilot.pause(0.5)
        svg_help = app.export_screenshot()
        (output_dir / "help_screen.svg").write_text(svg_help)
        await pilot.press("escape")
        await pilot.pause(0.3)

        # Advanced Options Screen
        await pilot.press("a")
        await pilot.pause(0.5)
        svg_advanced = app.export_screenshot()
        (output_dir / "advanced_screen.svg").write_text(svg_advanced)
        await pilot.press("escape")
        await pilot.pause(0.3)


async def generate_screenshots(output_dir: pathlib.Path) -> None:
    """Capture SVG screenshots of all main Textual screens in netflix-narc."""
    output_dir.mkdir(parents=True, exist_ok=True)
    sample_csv = pathlib.Path("NetflixViewingHistory.csv")
    csv_to_use = sample_csv if sample_csv.exists() else None

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_cache_dir = pathlib.Path(tmp_dir)
        records = get_sample_manual_records()

        await _capture_onboarding_screenshots(output_dir, records, tmp_cache_dir)
        await _capture_main_app_screenshots(output_dir, records, tmp_cache_dir, csv_to_use)

    print(f"All screenshots generated successfully in {output_dir}/")


def main() -> None:
    """Main entrypoint for script execution."""
    args = parse_args()
    asyncio.run(generate_screenshots(args.output_dir))


if __name__ == "__main__":
    main()
