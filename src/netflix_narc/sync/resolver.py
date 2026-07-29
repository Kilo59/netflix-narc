"""Conflict resolution engine implementing Last-Write-Wins (LWW) strategies."""

from __future__ import annotations

import datetime as dt
import logging

from netflix_narc.sync.models import DossierSyncItem, SettingsSyncItem, SyncBundle

logger = logging.getLogger(__name__)


def _parse_utc_timestamp(ts_str: str) -> dt.datetime:
    """Parse ISO timestamp string into a timezone-aware UTC datetime."""
    try:
        parsed = dt.datetime.fromisoformat(ts_str)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=dt.UTC)
        return parsed.astimezone(dt.UTC)
    except ValueError:
        logger.warning("Invalid ISO timestamp format %r; using epoch fallback", ts_str)
        return dt.datetime.fromtimestamp(0, tz=dt.UTC)


class ConflictResolver:
    """Merges local and remote sync bundles using field & timestamp rules."""

    def merge_dossiers(
        self,
        local_items: list[DossierSyncItem],
        remote_items: list[DossierSyncItem],
    ) -> list[DossierSyncItem]:
        """Merge local and remote dossier items using Last-Write-Wins per title."""
        merged: dict[str, DossierSyncItem] = {}

        for item in local_items:
            merged[item.title] = item

        for remote_item in remote_items:
            title = remote_item.title
            if title not in merged:
                merged[title] = remote_item
                continue

            local_item = merged[title]
            local_ts = _parse_utc_timestamp(local_item.updated_at)
            remote_ts = _parse_utc_timestamp(remote_item.updated_at)

            if remote_ts >= local_ts:
                merged[title] = remote_item

        return list(merged.values())

    def merge_settings(
        self,
        local_settings: SettingsSyncItem | None,
        remote_settings: SettingsSyncItem | None,
    ) -> SettingsSyncItem | None:
        """Merge local and remote settings based on timestamp."""
        if local_settings is None:
            return remote_settings
        if remote_settings is None:
            return local_settings

        local_ts = _parse_utc_timestamp(local_settings.updated_at)
        remote_ts = _parse_utc_timestamp(remote_settings.updated_at)

        return remote_settings if remote_ts >= local_ts else local_settings

    def merge_bundles(self, local_bundle: SyncBundle, remote_bundle: SyncBundle) -> SyncBundle:
        """Combine local and remote bundles into a unified resolved bundle."""
        merged_dossiers = self.merge_dossiers(
            local_bundle.evidence_locker,
            remote_bundle.evidence_locker,
        )
        merged_settings = self.merge_settings(
            local_bundle.settings,
            remote_bundle.settings,
        )

        now_str = dt.datetime.now(dt.UTC).isoformat()
        return SyncBundle(
            version=max(local_bundle.version, remote_bundle.version),
            client_id=local_bundle.client_id,
            timestamp=now_str,
            settings=merged_settings,
            evidence_locker=merged_dossiers,
        )
