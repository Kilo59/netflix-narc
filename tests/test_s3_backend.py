"""Unit tests for S3StorageBackend using respx for HTTP mocking."""

from __future__ import annotations

import httpx
import pytest
import respx
from pydantic import SecretStr

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


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
