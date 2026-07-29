"""Unit tests for WebDAVStorageBackend using respx HTTP mocking."""

from __future__ import annotations

import httpx
import pytest
import respx
from pydantic import SecretStr

from netflix_narc.sync.backend import StorageAuthError, StorageBackendError
from netflix_narc.sync.models import DossierSyncItem, SyncBundle
from netflix_narc.sync.webdav import WebDAVStorageBackend


def _make_webdav_backend() -> WebDAVStorageBackend:
    return WebDAVStorageBackend(
        webdav_url="https://nextcloud.example.com/remote.php/dav/files/user",
        username="user",
        password=SecretStr("secret-pass"),
        remote_path="netflix-narc",
    )


@pytest.mark.asyncio
async def test_webdav_backend_initialize_success() -> None:
    """Test successful WebDAV initialize with PROPFIND 200."""
    backend = _make_webdav_backend()
    url = "https://nextcloud.example.com/remote.php/dav/files/user/netflix-narc/"

    with respx.mock(assert_all_called=False) as respx_mock:
        respx_mock.request("PROPFIND", url).respond(status_code=200)
        async with httpx.AsyncClient() as client:
            backend._client = client
            await backend.initialize()


@pytest.mark.asyncio
async def test_webdav_backend_initialize_creates_folder_on_404() -> None:
    """Test initialize attempts MKCOL when PROPFIND returns 404."""
    backend = _make_webdav_backend()
    url = "https://nextcloud.example.com/remote.php/dav/files/user/netflix-narc/"

    with respx.mock(assert_all_called=False) as respx_mock:
        respx_mock.request("PROPFIND", url).respond(status_code=404)
        respx_mock.request("MKCOL", url).respond(status_code=201)
        async with httpx.AsyncClient() as client:
            backend._client = client
            await backend.initialize()


@pytest.mark.asyncio
async def test_webdav_backend_initialize_raises_auth_error() -> None:
    """Test initialize raises StorageAuthError on 401 Unauthorized."""
    backend = _make_webdav_backend()
    url = "https://nextcloud.example.com/remote.php/dav/files/user/netflix-narc/"

    with respx.mock(assert_all_called=False) as respx_mock:
        respx_mock.request("PROPFIND", url).respond(status_code=401)
        async with httpx.AsyncClient() as client:
            backend._client = client
            with pytest.raises(StorageAuthError):
                await backend.initialize()


@pytest.mark.asyncio
async def test_webdav_backend_test_connection() -> None:
    """Test test_connection returns True for 200/207 and False for 401/network error."""
    backend = _make_webdav_backend()
    url = "https://nextcloud.example.com/remote.php/dav/files/user/netflix-narc/"

    # 1. 200 -> True
    with respx.mock(assert_all_called=False) as respx_mock:
        respx_mock.request("PROPFIND", url).respond(status_code=200)
        async with httpx.AsyncClient() as client:
            backend._client = client
            assert await backend.test_connection() is True

    # 2. 401 -> False
    with respx.mock(assert_all_called=False) as respx_mock:
        respx_mock.request("PROPFIND", url).respond(status_code=401)
        async with httpx.AsyncClient() as client:
            backend._client = client
            assert await backend.test_connection() is False

    # 3. HTTP Network Error -> False
    with respx.mock(assert_all_called=False) as respx_mock:
        respx_mock.request("PROPFIND", url).side_effect = httpx.ConnectError("Network down")
        async with httpx.AsyncClient() as client:
            backend._client = client
            assert await backend.test_connection() is False


@pytest.mark.asyncio
async def test_webdav_backend_upload_and_download() -> None:
    """Test WebDAV upload_bundle and download_bundle."""
    backend = _make_webdav_backend()
    base_url = "https://nextcloud.example.com/remote.php/dav/files/user/netflix-narc/"
    bundle_url = "https://nextcloud.example.com/remote.php/dav/files/user/netflix-narc/bundle.json"
    manifest_url = (
        "https://nextcloud.example.com/remote.php/dav/files/user/netflix-narc/manifest.json"
    )

    bundle = SyncBundle(
        client_id="webdav-client",
        evidence_locker=[
            DossierSyncItem(title="Wednesday", content_rating="12", user_rating=4.0),
        ],
    )

    with respx.mock(assert_all_called=False) as respx_mock:
        respx_mock.request("PROPFIND", base_url).respond(status_code=200)
        respx_mock.put(bundle_url).respond(status_code=201)
        respx_mock.put(manifest_url).respond(status_code=201)

        async with httpx.AsyncClient() as client:
            backend._client = client
            await backend.upload_bundle(bundle)

    # Test download
    bundle_json = bundle.model_dump(mode="json")
    with respx.mock(assert_all_called=False) as respx_mock:
        respx_mock.get(bundle_url).respond(status_code=200, json=bundle_json)

        async with httpx.AsyncClient() as client:
            backend._client = client
            downloaded = await backend.download_bundle()

        assert downloaded is not None
        assert downloaded.client_id == "webdav-client"
        assert downloaded.evidence_locker[0].title == "Wednesday"


@pytest.mark.asyncio
async def test_webdav_backend_download_bundle_raises_on_malformed_json() -> None:
    """Test download_bundle raises StorageBackendError on malformed JSON."""
    backend = _make_webdav_backend()
    bundle_url = "https://nextcloud.example.com/remote.php/dav/files/user/netflix-narc/bundle.json"

    with respx.mock(assert_all_called=False) as respx_mock:
        respx_mock.get(bundle_url).respond(status_code=200, text="not valid json")
        async with httpx.AsyncClient() as client:
            backend._client = client
            with pytest.raises(StorageBackendError):
                await backend.download_bundle()


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
