"""Storage and synchronization abstractions for Netflix Narc."""

from __future__ import annotations

from netflix_narc.sync.backend import StorageBackend, StorageBackendError
from netflix_narc.sync.engine import SyncEngine, SyncResult
from netflix_narc.sync.local_folder import LocalStorageBackend
from netflix_narc.sync.models import DossierSyncItem, SettingsSyncItem, SyncBundle, SyncManifest
from netflix_narc.sync.resolver import ConflictResolver
from netflix_narc.sync.s3 import S3StorageBackend
from netflix_narc.sync.webdav import WebDAVStorageBackend

__all__ = [
    "ConflictResolver",
    "DossierSyncItem",
    "LocalStorageBackend",
    "S3StorageBackend",
    "SettingsSyncItem",
    "StorageBackend",
    "StorageBackendError",
    "SyncBundle",
    "SyncEngine",
    "SyncManifest",
    "SyncResult",
    "WebDAVStorageBackend",
]
