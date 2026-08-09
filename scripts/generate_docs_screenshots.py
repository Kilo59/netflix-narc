"""Alias wrapper for generate_tui_screenshots.py for backward compatibility."""

from __future__ import annotations

import pathlib
import sys

_SCRIPTS_DIR = pathlib.Path(__file__).parent.resolve()
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import generate_tui_screenshots  # noqa: E402

generate_screenshots = generate_tui_screenshots.generate_screenshots
main = generate_tui_screenshots.main
parse_args = generate_tui_screenshots.parse_args

__all__ = ["generate_screenshots", "main", "parse_args"]

if __name__ == "__main__":
    main()
