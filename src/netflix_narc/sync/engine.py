"""High-level synchronization engine coordinating local persistence and remote backends."""

from __future__ import annotations

import datetime as dt
import logging
import uuid
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from netflix_narc.manual_db import EvidenceLocker
    from netflix_narc.settings import Settings

from netflix_narc.sync.backend import StorageBackend, StorageBackendError
from netflix_narc.sync.models import DossierSyncItem, SettingsSyncItem, SyncBundle
from netflix_narc.sync.resolver import ConflictResolver

logger = logging.getLogger(__name__)


class SyncResult(BaseModel):
    """Summary of completed sync operation."""

    status: str  # "success", "up_to_date", "error"
    items_synced: int = 0
    message: str = ""


class SyncEngine:
    """Orchestrates reading state, interacting with StorageBackend, and resolving conflicts."""

    def __init__(
        self,
        backend: StorageBackend,
        locker: EvidenceLocker,
        settings: Settings | None = None,
        client_id: str | None = None,
        resolver: ConflictResolver | None = None,
    ) -> None:
        """Initialize SyncEngine."""
        self.backend = backend
        self.locker = locker
        self.settings = settings
        self.client_id = client_id or f"client-{uuid.uuid4().hex[:8]}"
        self.resolver = resolver or ConflictResolver()

    async def create_local_bundle(self) -> SyncBundle:
        """Dump local EvidenceLocker dossiers and Settings into a SyncBundle."""
        dossiers_raw = await self.locker.dump_dossiers()
        dossier_items = [DossierSyncItem.model_validate(d) for d in dossiers_raw]

        settings_item: SettingsSyncItem | None = None
        if self.settings is not None:
            settings_item = SettingsSyncItem(
                active_rating_provider=str(self.settings.active_rating_provider),
                scoring_mode=str(self.settings.scoring_mode),
                child_age_range=self.settings.child_age_range,
                max_age_rating=self.settings.max_age_rating,
                min_quality_rating=self.settings.min_quality_rating,
                category_weights=self.settings.weights.model_dump(),
                updated_at=dt.datetime.now(dt.UTC).isoformat(),
            )

        now_str = dt.datetime.now(dt.UTC).isoformat()
        return SyncBundle(
            client_id=self.client_id,
            timestamp=now_str,
            settings=settings_item,
            evidence_locker=dossier_items,
        )

    async def apply_bundle_to_local(self, bundle: SyncBundle) -> int:
        """Apply resolved bundle dossiers back into local EvidenceLocker."""
        if not bundle.evidence_locker:
            return 0
        dossier_dicts = [item.model_dump() for item in bundle.evidence_locker]
        return await self.locker.load_dossiers(dossier_dicts)

    async def sync(self) -> SyncResult:
        """Perform full two-way synchronization."""
        try:
            local_bundle = await self.create_local_bundle()
            remote_bundle = await self.backend.download_bundle()

            if remote_bundle is None:
                # First sync to remote
                await self.backend.upload_bundle(local_bundle)
                return SyncResult(
                    status="success",
                    items_synced=len(local_bundle.evidence_locker),
                    message="Uploaded initial local bundle to remote storage.",
                )

            # Resolve local and remote bundles
            resolved_bundle = self.resolver.merge_bundles(local_bundle, remote_bundle)

            # Save resolved back to local locker
            applied_count = await self.apply_bundle_to_local(resolved_bundle)

            # Upload resolved bundle back to remote storage
            await self.backend.upload_bundle(resolved_bundle)

            return SyncResult(
                status="success",
                items_synced=applied_count,
                message=f"Sync completed successfully. {applied_count} dossiers synchronized.",
            )

        except StorageBackendError as exc:
            logger.exception("Sync operation failed")
            return SyncResult(
                status="error",
                items_synced=0,
                message=f"Sync failed: {exc}",
            )
