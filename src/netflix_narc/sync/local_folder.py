"""Local folder storage backend (iCloud, Dropbox, Syncthing, local path)."""

from __future__ import annotations

import json
import pathlib
import uuid
from typing import override

from netflix_narc.sync.backend import StorageBackend, StorageBackendError
from netflix_narc.sync.models import SyncBundle, SyncManifest


class LocalStorageBackend(StorageBackend):
    """Storage backend that reads/writes sync bundles to a local filesystem directory."""

    def __init__(self, sync_dir: pathlib.Path | str) -> None:
        """Initialize with target directory path."""
        self.sync_dir = pathlib.Path(sync_dir)

    @property
    def manifest_path(self) -> pathlib.Path:
        """Return path to remote sync manifest file."""
        return self.sync_dir / "manifest.json"

    @property
    def bundle_path(self) -> pathlib.Path:
        """Return path to active sync bundle file."""
        return self.sync_dir / "bundle.json"

    @override
    async def initialize(self) -> None:
        """Create sync directory if needed."""
        try:
            self.sync_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            msg = f"Failed to create sync directory {self.sync_dir}: {exc}"
            raise StorageBackendError(msg) from exc

    @override
    async def test_connection(self) -> bool:
        """Verify directory exists and is writable."""
        if not self.sync_dir.exists():
            try:
                self.sync_dir.mkdir(parents=True, exist_ok=True)
            except OSError:
                return False

        test_file = self.sync_dir / f".test_write_{uuid.uuid4().hex}"
        try:
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink()
        except OSError:
            return False
        else:
            return True

    @override
    async def get_manifest(self) -> SyncManifest | None:
        """Retrieve manifest.json if present."""
        if not self.manifest_path.exists():
            return None
        try:
            raw_text = self.manifest_path.read_text(encoding="utf-8")
            data = json.loads(raw_text)
            return SyncManifest.model_validate(data)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            msg = f"Failed to parse manifest at {self.manifest_path}: {exc}"
            raise StorageBackendError(msg) from exc

    @override
    async def upload_bundle(self, bundle: SyncBundle) -> None:
        """Write bundle.json and update manifest.json."""
        await self.initialize()

        bundle_data = bundle.model_dump(mode="json")
        bundle_text = json.dumps(bundle_data, indent=2)

        # Atomic write to bundle.json
        tmp_bundle = self.sync_dir / f".bundle_{uuid.uuid4().hex}.tmp"
        try:
            tmp_bundle.write_text(bundle_text, encoding="utf-8")
            tmp_bundle.replace(self.bundle_path)
        except OSError as exc:
            if tmp_bundle.exists():
                tmp_bundle.unlink(missing_ok=True)
            msg = f"Failed to write bundle file: {exc}"
            raise StorageBackendError(msg) from exc

        manifest = SyncManifest(
            latest_bundle_id=self.bundle_path.name,
            last_updated=bundle.timestamp,
            client_id=bundle.client_id,
            version=bundle.version,
        )
        manifest_data = manifest.model_dump(mode="json")
        manifest_text = json.dumps(manifest_data, indent=2)

        tmp_manifest = self.sync_dir / f".manifest_{uuid.uuid4().hex}.tmp"
        try:
            tmp_manifest.write_text(manifest_text, encoding="utf-8")
            tmp_manifest.replace(self.manifest_path)
        except OSError as exc:
            if tmp_manifest.exists():
                tmp_manifest.unlink(missing_ok=True)
            msg = f"Failed to write manifest file: {exc}"
            raise StorageBackendError(msg) from exc

    @override
    async def download_bundle(self) -> SyncBundle | None:
        """Read and parse bundle.json if present."""
        if not self.bundle_path.exists():
            return None
        try:
            raw_text = self.bundle_path.read_text(encoding="utf-8")
            data = json.loads(raw_text)
            return SyncBundle.model_validate(data)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            msg = f"Failed to parse sync bundle at {self.bundle_path}: {exc}"
            raise StorageBackendError(msg) from exc
