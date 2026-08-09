"""Alias wrapper for generate_tui_screenshots.py for backward compatibility."""

from __future__ import annotations

from generate_tui_screenshots import generate_screenshots, main, parse_args

__all__ = ["generate_screenshots", "main", "parse_args"]

if __name__ == "__main__":
    main()
