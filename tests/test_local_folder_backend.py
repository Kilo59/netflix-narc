"""Unit tests for LocalStorageBackend."""

from __future__ import annotations

import pathlib

import pytest

from netflix_narc.sync.local_folder import LocalStorageBackend
from netflix_narc.sync.models import DossierSyncItem, SyncBundle


@pytest.mark.asyncio
async def test_local_folder_backend_lifecycle(tmp_path: pathlib.Path) -> None:
    """Test full upload, download, and manifest retrieval with LocalStorageBackend."""
    sync_dir = tmp_path / "sync_folder"
    backend = LocalStorageBackend(sync_dir)

    await backend.initialize()
    assert sync_dir.exists()

    # Initial state should be empty
    manifest = await backend.get_manifest()
    assert manifest is None

    downloaded = await backend.download_bundle()
    assert downloaded is None

    # Test connection
    is_writable = await backend.test_connection()
    assert is_writable is True

    # Upload bundle
    bundle = SyncBundle(
        client_id="test-client",
        evidence_locker=[
            DossierSyncItem(title="Stranger Things", content_rating="14", user_rating=4.5),
        ],
    )
    await backend.upload_bundle(bundle)

    # Manifest and bundle should now exist
    manifest = await backend.get_manifest()
    assert manifest is not None
    assert manifest.client_id == "test-client"

    downloaded_bundle = await backend.download_bundle()
    assert downloaded_bundle is not None
    assert downloaded_bundle.client_id == "test-client"
    assert len(downloaded_bundle.evidence_locker) == 1
    assert downloaded_bundle.evidence_locker[0].title == "Stranger Things"


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
