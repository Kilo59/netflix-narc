"""Common interface behavioral tests for all StorageBackend implementations."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest

from netflix_narc.sync.backend import StorageBackendError
from netflix_narc.sync.local_folder import LocalStorageBackend
from netflix_narc.sync.models import DossierSyncItem, SyncBundle

if TYPE_CHECKING:
    import respx

    from netflix_narc.sync.backend import StorageBackend


@pytest.mark.asyncio
async def test_backend_download_missing_bundle_returns_none(
    storage_backend: StorageBackend,
    respx_mock: respx.MockRouter,
) -> None:
    """download_bundle() returns None when no bundle exists remotely."""
    respx_mock.get(url=re.compile(r".*bundle\.json$")).respond(status_code=404)
    assert await storage_backend.download_bundle() is None


@pytest.mark.asyncio
async def test_backend_get_manifest_missing_returns_none(
    storage_backend: StorageBackend,
    respx_mock: respx.MockRouter,
) -> None:
    """get_manifest() returns None when no manifest exists remotely."""
    respx_mock.get(url=re.compile(r".*manifest\.json$")).respond(status_code=404)
    assert await storage_backend.get_manifest() is None


@pytest.mark.asyncio
async def test_backend_upload_and_download_roundtrip(
    storage_backend: StorageBackend,
    respx_mock: respx.MockRouter,
) -> None:
    """upload_bundle() and download_bundle() roundtrip sync bundle data correctly."""
    bundle = SyncBundle(
        client_id="common-client",
        evidence_locker=[
            DossierSyncItem(title="Common Show", content_rating="16", user_rating=4.0)
        ],
    )
    bundle_data = bundle.model_dump(mode="json")

    respx_mock.put(url=re.compile(r".*bundle\.json$")).respond(status_code=201)
    respx_mock.put(url=re.compile(r".*manifest\.json$")).respond(status_code=201)
    respx_mock.get(url=re.compile(r".*bundle\.json$")).respond(status_code=200, json=bundle_data)

    await storage_backend.upload_bundle(bundle)
    downloaded = await storage_backend.download_bundle()

    assert downloaded is not None
    assert downloaded.client_id == "common-client"
    assert len(downloaded.evidence_locker) == 1
    assert downloaded.evidence_locker[0].title == "Common Show"


@pytest.mark.asyncio
async def test_backend_download_bundle_malformed_json_raises_error(
    storage_backend: StorageBackend,
    respx_mock: respx.MockRouter,
) -> None:
    """download_bundle() raises StorageBackendError when data is malformed JSON."""
    match storage_backend:
        case LocalStorageBackend():
            storage_backend.bundle_path.write_text("invalid json {", encoding="utf-8")
        case _:
            respx_mock.get(url=re.compile(r".*bundle\.json$")).respond(
                status_code=200, text="invalid json {"
            )

    with pytest.raises(StorageBackendError):
        await storage_backend.download_bundle()


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
