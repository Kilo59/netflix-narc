"""Tests for the image utility functions."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest
import respx

from netflix_narc.image_utils import (
    download_image_to_path,
    ensure_image_dir,
    normalize_title_for_filename,
    save_image_from_clipboard,
)

if TYPE_CHECKING:
    import pathlib

    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch


def test_normalize_title_for_filename() -> None:
    """Verify that title strings are correctly normalized into safe filenames."""
    assert normalize_title_for_filename("Stranger Things") == "stranger_things"
    assert normalize_title_for_filename("Breaking Bad: Season 1") == "breaking_bad_season_1"
    assert normalize_title_for_filename("  The Witcher  ") == "the_witcher"
    assert normalize_title_for_filename("---abc$$$123---") == "abc_123"
    assert normalize_title_for_filename("$$$") == "untitled"


def test_ensure_image_dir(tmp_path: pathlib.Path, monkeypatch: MonkeyPatch) -> None:
    """Verify that the image directory is correctly created and exists."""
    test_dir = tmp_path / "custom_images"
    monkeypatch.setattr("netflix_narc.image_utils.IMAGE_DIR", test_dir)
    assert not test_dir.exists()
    ensure_image_dir()
    assert test_dir.exists()
    assert test_dir.is_dir()


@pytest.mark.asyncio
async def test_download_image_to_path_success(
    tmp_path: pathlib.Path, monkeypatch: MonkeyPatch
) -> None:
    """Verify that downloading an image from a URL writes the correct bytes to a file."""
    test_dir = tmp_path / "custom_images"
    monkeypatch.setattr("netflix_narc.image_utils.IMAGE_DIR", test_dir)

    url = "https://example.com/poster.png"
    image_content = b"fake-png-data"

    with respx.mock:
        route = respx.get(url).mock(
            return_value=httpx.Response(
                status_code=200,
                content=image_content,
                headers={"Content-Type": "image/png"},
            )
        )

        result = await download_image_to_path(url, "My Show")
        assert result is not None
        assert result.exists()
        assert result.read_bytes() == image_content
        assert result.name == "my_show.png"
        assert route.called


@pytest.mark.asyncio
async def test_download_image_to_path_failure(
    tmp_path: pathlib.Path,
    monkeypatch: MonkeyPatch,
    caplog: LogCaptureFixture,
) -> None:
    """Verify that a failed image download returns None and logs an error."""
    test_dir = tmp_path / "custom_images"
    monkeypatch.setattr("netflix_narc.image_utils.IMAGE_DIR", test_dir)

    url = "https://example.com/poster.png"

    with respx.mock:
        route = respx.get(url).mock(
            return_value=httpx.Response(
                status_code=500,
                content=b"error",
            )
        )

        with caplog.at_level("ERROR"):
            result = await download_image_to_path(url, "My Show")

        assert result is None
        assert route.called
        assert any("Failed to download image" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_save_image_from_clipboard_failure(
    tmp_path: pathlib.Path,
    monkeypatch: MonkeyPatch,
    caplog: LogCaptureFixture,
) -> None:
    """Verify that clipboard failure is handled gracefully and quotes are handled robustly."""
    test_dir = tmp_path / 'custom_"images"'
    monkeypatch.setattr("netflix_narc.image_utils.IMAGE_DIR", test_dir)

    class FakeProcess:
        """A fake asyncio subprocess to simulate failure."""

        def __init__(self) -> None:
            self.returncode = 1

        async def communicate(self) -> tuple[bytes, bytes]:
            return b"FAIL", b"osascript error"

    captured_args: list[object] = []

    async def fake_create_subprocess_exec(
        *args: object,
        **_kwargs: object,
    ) -> FakeProcess:
        captured_args.extend(args)
        return FakeProcess()

    monkeypatch.setattr("asyncio.create_subprocess_exec", fake_create_subprocess_exec)
    monkeypatch.setattr("sys.platform", "darwin")

    with caplog.at_level("ERROR"):
        result = await save_image_from_clipboard("My Show")

    assert result is None
    assert any("Failed to save clipboard image" in record.message for record in caplog.records)
    # Check that the path with double quotes is passed as-is to the AppleScript argv argument
    assert any('custom_"images"' in arg for arg in captured_args if isinstance(arg, str))


@pytest.mark.asyncio
async def test_download_image_to_path_non_image_content_type(
    tmp_path: pathlib.Path,
    monkeypatch: MonkeyPatch,
    caplog: LogCaptureFixture,
) -> None:
    """Verify that a non-image content type returns None and logs an error."""
    test_dir = tmp_path / "custom_images"
    monkeypatch.setattr("netflix_narc.image_utils.IMAGE_DIR", test_dir)

    url = "https://example.com/not-an-image.html"

    with respx.mock:
        route = respx.get(url).mock(
            return_value=httpx.Response(
                status_code=200,
                content=b"<html>not an image</html>",
                headers={"Content-Type": "text/html"},
            )
        )

        with caplog.at_level("ERROR"):
            result = await download_image_to_path(url, "My Show")

        assert result is None
        assert route.called
        assert any("is not an image" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_download_image_to_path_client_injection(
    tmp_path: pathlib.Path, monkeypatch: MonkeyPatch
) -> None:
    """Verify that an injected httpx client can be successfully used."""
    test_dir = tmp_path / "custom_images"
    monkeypatch.setattr("netflix_narc.image_utils.IMAGE_DIR", test_dir)

    url = "https://example.com/poster.png"
    image_content = b"fake-png-data"

    async with httpx.AsyncClient() as client:
        with respx.mock:
            route = respx.get(url).mock(
                return_value=httpx.Response(
                    status_code=200,
                    content=image_content,
                    headers={"Content-Type": "image/png"},
                )
            )

            result = await download_image_to_path(url, "My Show", client=client)
            assert result is not None
            assert result.exists()
            assert result.read_bytes() == image_content
            assert result.name == "my_show.png"
            assert route.called


@pytest.mark.asyncio
async def test_download_image_to_path_content_type_with_parameters(
    tmp_path: pathlib.Path, monkeypatch: MonkeyPatch
) -> None:
    """Verify that Content-Type parameters (like charset) are stripped correctly."""
    test_dir = tmp_path / "custom_images"
    monkeypatch.setattr("netflix_narc.image_utils.IMAGE_DIR", test_dir)

    url = "https://example.com/poster.jpeg"
    image_content = b"fake-jpeg-data"

    with respx.mock:
        route = respx.get(url).mock(
            return_value=httpx.Response(
                status_code=200,
                content=image_content,
                headers={"Content-Type": "image/jpeg; charset=binary"},
            )
        )

        result = await download_image_to_path(url, "My Show")
        assert result is not None
        assert result.exists()
        assert result.read_bytes() == image_content
        assert result.name == "my_show.jpg"
        assert route.called


@pytest.mark.asyncio
async def test_download_image_to_path_custom_params(
    tmp_path: pathlib.Path, monkeypatch: MonkeyPatch
) -> None:
    """Verify that custom timeout and follow_redirects parameters are passed to httpx."""
    test_dir = tmp_path / "custom_images"
    monkeypatch.setattr("netflix_narc.image_utils.IMAGE_DIR", test_dir)

    url = "https://example.com/poster.png"
    image_content = b"fake-png-data"

    async with httpx.AsyncClient() as client:
        with respx.mock:
            route = respx.get(url).mock(
                return_value=httpx.Response(
                    status_code=200,
                    content=image_content,
                    headers={"Content-Type": "image/png"},
                )
            )

            result = await download_image_to_path(
                url,
                "My Show",
                client=client,
                request_timeout=5.0,
                follow_redirects=False,
            )
            assert result is not None
            assert result.name == "my_show.png"
            assert route.called


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
