"""Unit tests for S3StorageBackend using respx for HTTP mocking."""

from __future__ import annotations

import httpx
import pytest
import respx
from pydantic import SecretStr

from netflix_narc.sync.backend import StorageAuthError, StorageBackendError, StorageConnectionError
from netflix_narc.sync.models import DossierSyncItem, SyncBundle
from netflix_narc.sync.s3 import S3StorageBackend


@pytest.mark.asyncio
async def test_s3_backend_upload_and_download() -> None:
    """Test S3StorageBackend upload and download using respx HTTP mocking."""
    endpoint = "https://r2.cloudflarestorage.com"
    bucket = "my-sync-bucket"
    backend = S3StorageBackend(
        endpoint_url=endpoint,
        bucket_name=bucket,
        access_key_id=SecretStr("fake-access-key"),
        secret_access_key=SecretStr("fake-secret-key"),
        prefix="narc-data",
    )

    bundle_url = "https://r2.cloudflarestorage.com/my-sync-bucket/narc-data/bundle.json"
    manifest_url = "https://r2.cloudflarestorage.com/my-sync-bucket/narc-data/manifest.json"

    bundle = SyncBundle(
        client_id="test-client-s3",
        evidence_locker=[
            DossierSyncItem(title="Ozark", content_rating="18", user_rating=4.8),
        ],
    )

    with respx.mock(assert_all_called=False) as respx_mock:
        respx_mock.put(bundle_url).respond(status_code=200)
        respx_mock.put(manifest_url).respond(status_code=200)

        async with httpx.AsyncClient() as client:
            backend._client = client
            await backend.upload_bundle(bundle)

        assert respx_mock.calls.call_count == 2

    # Test download
    bundle_data = bundle.model_dump(mode="json")
    with respx.mock(assert_all_called=False) as respx_mock:
        respx_mock.get(bundle_url).respond(status_code=200, json=bundle_data)

        async with httpx.AsyncClient() as client:
            backend._client = client
            downloaded = await backend.download_bundle()

        assert downloaded is not None
        assert downloaded.client_id == "test-client-s3"
        assert downloaded.evidence_locker[0].title == "Ozark"


@pytest.mark.asyncio
async def test_s3_backend_sigv4_auth_header_injection() -> None:
    """Verify S3SigV4Auth adds AWS4-HMAC-SHA256 Authorization header when client is auto-created."""
    backend = S3StorageBackend(
        endpoint_url="https://r2.cloudflarestorage.com",
        bucket_name="my-bucket",
        access_key_id=SecretStr("my-access-key"),
        secret_access_key=SecretStr("my-secret-key"),
    )
    url = "https://r2.cloudflarestorage.com/my-bucket/netflix-narc/.test_ping"

    with respx.mock(assert_all_called=False) as respx_mock:
        route = respx_mock.head(url).respond(status_code=200)
        assert await backend.test_connection() is True
        assert route.called
        last_req = route.calls.last.request
        auth_header = last_req.headers["authorization"]
        assert auth_header.startswith("AWS4-HMAC-SHA256 Credential=my-access-key/")


@pytest.mark.asyncio
async def test_s3_backend_raises_storage_auth_error_on_403() -> None:
    """initialize() should raise StorageAuthError when S3 returns 403 Forbidden."""
    backend = S3StorageBackend(
        endpoint_url="https://r2.cloudflarestorage.com",
        bucket_name="my-bucket",
        access_key_id=SecretStr("key"),
        secret_access_key=SecretStr("secret"),
    )
    manifest_url = "https://r2.cloudflarestorage.com/my-bucket/netflix-narc/manifest.json"

    with respx.mock(assert_all_called=False) as respx_mock:
        respx_mock.head(manifest_url).respond(status_code=403)
        async with httpx.AsyncClient() as client:
            backend._client = client
            with pytest.raises(StorageAuthError):
                await backend.initialize()


@pytest.mark.asyncio
async def test_s3_backend_raises_storage_connection_error() -> None:
    """initialize() should raise StorageConnectionError on network connection failure."""
    backend = S3StorageBackend(
        endpoint_url="https://r2.cloudflarestorage.com",
        bucket_name="my-bucket",
        access_key_id=SecretStr("key"),
        secret_access_key=SecretStr("secret"),
    )
    manifest_url = "https://r2.cloudflarestorage.com/my-bucket/netflix-narc/manifest.json"

    with respx.mock(assert_all_called=False) as respx_mock:
        respx_mock.head(manifest_url).side_effect = httpx.ConnectError("Failed to connect")
        async with httpx.AsyncClient() as client:
            backend._client = client
            with pytest.raises(StorageConnectionError):
                await backend.initialize()


@pytest.mark.asyncio
async def test_s3_backend_download_bundle_raises_on_malformed_json() -> None:
    """download_bundle() should raise StorageBackendError when response body is not valid JSON."""
    backend = S3StorageBackend(
        endpoint_url="https://r2.cloudflarestorage.com",
        bucket_name="my-bucket",
        access_key_id=SecretStr("key"),
        secret_access_key=SecretStr("secret"),
    )
    bundle_url = "https://r2.cloudflarestorage.com/my-bucket/netflix-narc/bundle.json"

    with respx.mock(assert_all_called=False) as respx_mock:
        respx_mock.get(bundle_url).respond(status_code=200, text="not valid json")
        async with httpx.AsyncClient() as client:
            backend._client = client
            with pytest.raises(StorageBackendError):
                await backend.download_bundle()


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
