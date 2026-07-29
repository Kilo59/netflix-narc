"""Storage backend protocol and exception definitions for Netflix Narc."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from netflix_narc.sync.models import SyncBundle, SyncManifest


class StorageBackendError(Exception):
    """Base exception raised for storage backend errors."""


class StorageConnectionError(StorageBackendError):
    """Raised when connecting to a remote storage provider fails."""


class StorageAuthError(StorageBackendError):
    """Raised when authentication with a storage provider fails."""


@runtime_checkable
class StorageBackend(Protocol):
    """Abstract protocol for user-provided storage backends (BYOS)."""

    async def initialize(self) -> None:
        """Initialize the storage backend (e.g. verify path, test auth)."""
        ...

    async def test_connection(self) -> bool:
        """Validate credentials and permissions."""
        ...

    async def get_manifest(self) -> SyncManifest | None:
        """Retrieve the latest remote sync manifest."""
        ...

    async def upload_bundle(self, bundle: SyncBundle) -> None:
        """Upload a new state snapshot bundle to remote storage."""
        ...

    async def download_bundle(self) -> SyncBundle | None:
        """Fetch the latest state snapshot bundle from remote storage."""
        ...
