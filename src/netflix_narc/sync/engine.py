"""High-level synchronization engine coordinating local persistence and remote backends."""

from __future__ import annotations

import datetime as dt
import logging
import pathlib
import uuid
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from netflix_narc.manual_db import EvidenceLocker
    from netflix_narc.settings import Settings

from netflix_narc.persistence import update_env_file
from netflix_narc.settings import CategoryWeights, RatingProviderType, ScoringMode
from netflix_narc.sync.backend import StorageBackend, StorageBackendError
from netflix_narc.sync.models import SettingsSyncItem, SyncBundle
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

    def _get_settings_updated_at(self) -> dt.datetime:
        """Return last modified time of local .env file, or epoch if non-existent."""
        if self.settings is None:
            return dt.datetime.fromtimestamp(0, tz=dt.UTC)

        env_file_path = self.settings.model_config.get("env_file")
        if env_file_path:
            p = pathlib.Path(str(env_file_path))
            if p.exists():
                return dt.datetime.fromtimestamp(p.stat().st_mtime, tz=dt.UTC)
        return dt.datetime.fromtimestamp(0, tz=dt.UTC)

    async def create_local_bundle(self) -> SyncBundle:
        """Dump local EvidenceLocker dossiers and Settings into a SyncBundle."""
        dossiers = await self.locker.dump_dossiers()

        settings_item: SettingsSyncItem | None = None
        if self.settings is not None:
            settings_item = SettingsSyncItem(
                active_rating_provider=str(self.settings.active_rating_provider),
                scoring_mode=str(self.settings.scoring_mode),
                child_age_range=self.settings.child_age_range,
                max_age_rating=self.settings.max_age_rating,
                min_quality_rating=self.settings.min_quality_rating,
                category_weights=self.settings.weights.model_dump(),
                updated_at=self._get_settings_updated_at(),
            )

        return SyncBundle(
            client_id=self.client_id,
            timestamp=dt.datetime.now(dt.UTC),
            settings=settings_item,
            evidence_locker=dossiers,
        )

    def _apply_settings(self, item: SettingsSyncItem) -> None:
        """Update in-memory Settings object and persist to .env file."""
        if self.settings is None:
            return

        if item.active_rating_provider:
            self.settings.active_rating_provider = RatingProviderType(item.active_rating_provider)
        if item.scoring_mode:
            self.settings.scoring_mode = ScoringMode(item.scoring_mode)
        if item.child_age_range is not None:
            self.settings.child_age_range = item.child_age_range
        if item.max_age_rating is not None:
            self.settings.max_age_rating = item.max_age_rating
        if item.min_quality_rating is not None:
            self.settings.min_quality_rating = item.min_quality_rating
        if item.category_weights:
            self.settings.weights = CategoryWeights.model_validate(item.category_weights)

        extra_env = {
            "SCORING_MODE": str(self.settings.scoring_mode),
            "MAX_AGE_RATING": str(self.settings.max_age_rating),
            "MIN_QUALITY_RATING": str(self.settings.min_quality_rating),
        }
        api_key = (
            self.settings.omdb_api_key
            if self.settings.active_rating_provider == RatingProviderType.OMDB
            else self.settings.csm_api_key
        )

        env_file_path = self.settings.model_config.get("env_file")
        resolved_env_path = pathlib.Path(str(env_file_path)) if env_file_path else None

        update_env_file(
            provider=self.settings.active_rating_provider,
            api_key=api_key,
            env_path=resolved_env_path,
            child_age_range=self.settings.child_age_range,
            weights=self.settings.weights,
            extra_env=extra_env,
        )

    async def apply_bundle_to_local(self, bundle: SyncBundle) -> int:
        """Apply resolved bundle dossiers and settings back into local state."""
        if bundle.settings is not None:
            self._apply_settings(bundle.settings)

        if not bundle.evidence_locker:
            return 0
        return await self.locker.load_dossiers(bundle.evidence_locker)

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

            # Save resolved back to local locker and settings
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
