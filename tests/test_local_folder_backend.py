"""Unit tests for LocalStorageBackend."""

from __future__ import annotations

import pathlib

import pytest

from netflix_narc.sync.backend import StorageBackendError, StorageConnectionError
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


@pytest.mark.asyncio
async def test_local_folder_backend_initialize_fails_when_path_is_file(
    tmp_path: pathlib.Path,
) -> None:
    """initialize() should raise StorageConnectionError when target path is a file."""
    file_path = tmp_path / "not_a_dir"
    file_path.write_text("I am a file", encoding="utf-8")

    backend = LocalStorageBackend(file_path)
    with pytest.raises(StorageConnectionError, match="exists and is a file"):
        await backend.initialize()


@pytest.mark.asyncio
async def test_local_folder_backend_test_connection_fails_on_unwritable_dir(
    tmp_path: pathlib.Path,
) -> None:
    """test_connection() should return False when directory is unwritable."""
    sync_dir = tmp_path / "readonly_dir"
    backend = LocalStorageBackend(sync_dir)
    await backend.initialize()

    original_mode = sync_dir.stat().st_mode
    sync_dir.chmod(0o500)
    try:
        assert await backend.test_connection() is False
    finally:
        sync_dir.chmod(original_mode)


@pytest.mark.asyncio
async def test_local_folder_backend_get_manifest_raises_on_malformed_json(
    tmp_path: pathlib.Path,
) -> None:
    """get_manifest() should raise StorageBackendError on malformed JSON."""
    sync_dir = tmp_path / "sync_folder"
    backend = LocalStorageBackend(sync_dir)
    await backend.initialize()

    manifest_path = backend.manifest_path
    manifest_path.write_text("malformed json {", encoding="utf-8")

    with pytest.raises(StorageBackendError):
        await backend.get_manifest()


@pytest.mark.asyncio
async def test_local_folder_backend_download_bundle_raises_on_malformed_json(
    tmp_path: pathlib.Path,
) -> None:
    """download_bundle() should raise StorageBackendError on malformed JSON."""
    sync_dir = tmp_path / "sync_folder"
    backend = LocalStorageBackend(sync_dir)
    await backend.initialize()

    bundle_path = backend.bundle_path
    bundle_path.write_text("invalid json content", encoding="utf-8")

    with pytest.raises(StorageBackendError):
        await backend.download_bundle()


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
