"""Image fetching and clipboard utilities."""

from __future__ import annotations

import asyncio
import logging
import pathlib
import re
import subprocess

import httpx

logger = logging.getLogger(__name__)

IMAGE_DIR = pathlib.Path(".evidence_images")


def ensure_image_dir() -> None:
    """Ensure the evidence images directory exists."""
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)


def normalize_title_for_filename(title: str) -> str:
    """Normalize a title string to be safe for filenames."""
    # Convert to lowercase
    title = title.lower()
    # Replace anything that is not a letter or number with underscores
    title = re.sub(r"[^a-z0-9]", "_", title)
    # Deduplicate underscores
    title = re.sub(r"_+", "_", title)
    # Strip leading/trailing underscores
    return title.strip("_")


async def save_image_from_clipboard(title: str) -> pathlib.Path | None:
    """Read image from macOS clipboard using osascript and save it locally."""
    ensure_image_dir()
    norm_title = normalize_title_for_filename(title)
    filepath = IMAGE_DIR / f"{norm_title}.png"

    script = f"""
    try
        set theFile to (open for access POSIX file "{filepath.absolute()}" with write permission)
        set eof of theFile to 0
        write (the clipboard as «class PNGf») to theFile
        close access theFile
        return "SUCCESS"
    on error
        try
            close access theFile
        end try
        return "FAIL"
    end try
    """

    process = await asyncio.create_subprocess_exec(
        "osascript",
        "-e",
        script,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()

    if process.returncode == 0 and "SUCCESS" in stdout.decode("utf-8"):
        return filepath
    logger.error("Failed to save clipboard image: %s", stderr.decode("utf-8"))
    return None


async def download_image_to_path(url: str, title: str) -> pathlib.Path | None:
    """Download an image from a URL and save it locally."""
    ensure_image_dir()
    norm_title = normalize_title_for_filename(title)

    # Try to extract extension from URL, otherwise default to .jpg
    # Only keep standard image extensions, else default to .jpg
    ext = ".jpg"
    match = re.search(r"\.(jpg|jpeg|png|webp|gif)", url, re.IGNORECASE)
    if match:
        ext = match.group(0).lower()

    filepath = IMAGE_DIR / f"{norm_title}{ext}"

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, follow_redirects=True, timeout=10.0)
            resp.raise_for_status()

            # Use asyncio.to_thread for non-blocking file IO
            await asyncio.to_thread(filepath.write_bytes, resp.content)

            return filepath
    except Exception:
        logger.exception("Failed to download image from %s", url)
        return None
