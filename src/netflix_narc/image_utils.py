"""Image fetching and clipboard utilities."""

from __future__ import annotations

import asyncio
import logging
import pathlib
import re
import subprocess
import sys
from typing import Any

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
    normalized = title.strip("_")
    return normalized or "untitled"


async def save_image_from_clipboard(title: str) -> pathlib.Path | None:
    """Read image from macOS clipboard using osascript and save it locally."""
    if sys.platform != "darwin":
        logger.warning("Clipboard image saving is only supported on macOS.")
        return None

    ensure_image_dir()
    norm_title = normalize_title_for_filename(title)
    filepath = IMAGE_DIR / f"{norm_title}.png"

    script = """
    on run argv
        set targetPath to item 1 of argv
        try
            set theFile to (open for access POSIX file targetPath with write permission)
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
    end run
    """

    process = await asyncio.create_subprocess_exec(
        "osascript",
        "-e",
        script,
        str(filepath.absolute()),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()

    if process.returncode == 0 and "SUCCESS" in stdout.decode("utf-8"):
        return filepath
    logger.error("Failed to save clipboard image: %s", stderr.decode("utf-8"))
    return None


def _resolve_image_extension(resp: httpx.Response, url: str) -> str | None:
    """Resolve the file extension from Content-Type header or fallback to URL."""
    raw_content_type = resp.headers.get("content-type", "").lower()
    content_type = raw_content_type.split(";", 1)[0].strip()
    if not content_type.startswith("image/"):
        logger.error("Content type %s is not an image for URL %s", raw_content_type, url)
        return None

    ext_map = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }
    ext = ext_map.get(content_type)
    if not ext:
        match = re.search(r"\.(jpg|jpeg|png|webp|gif)", url, re.IGNORECASE)
        ext = match.group(0).lower() if match else ".jpg"
    return ext


async def _execute_download_request(
    url: str,
    client: httpx.AsyncClient | None,
    request_timeout: float | httpx.Timeout | None,
    *,
    follow_redirects: bool | None,
) -> httpx.Response:
    """Execute the HTTP request to download the image, returning the Response."""
    if client is not None:
        kwargs: dict[str, Any] = {}
        if request_timeout is not None:
            kwargs["timeout"] = request_timeout
        if follow_redirects is not None:
            kwargs["follow_redirects"] = follow_redirects
        resp = await client.get(url, **kwargs)
        resp.raise_for_status()
        return resp

    to_val = 10.0 if request_timeout is None else request_timeout
    fr_val = True if follow_redirects is None else follow_redirects
    async with httpx.AsyncClient() as new_client:
        resp = await new_client.get(url, timeout=to_val, follow_redirects=fr_val)
        resp.raise_for_status()
        return resp


async def download_image_to_path(
    url: str,
    title: str,
    client: httpx.AsyncClient | None = None,
    *,
    request_timeout: float | httpx.Timeout | None = None,
    follow_redirects: bool | None = None,
) -> pathlib.Path | None:
    """Download an image from a URL and save it locally."""
    ensure_image_dir()
    norm_title = normalize_title_for_filename(title)

    try:
        resp = await _execute_download_request(
            url,
            client,
            request_timeout,
            follow_redirects=follow_redirects,
        )

        # Use our helper to validate content type and resolve extension
        ext = _resolve_image_extension(resp, url)
        if ext is None:
            return None

        filepath = IMAGE_DIR / f"{norm_title}{ext}"

        # Use asyncio.to_thread for non-blocking file IO
        await asyncio.to_thread(filepath.write_bytes, resp.content)

    except Exception:
        logger.exception("Failed to download image from %s", url)
        return None
    else:
        return filepath
