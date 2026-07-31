"""Conflict resolution engine implementing Last-Write-Wins (LWW) strategies."""

from __future__ import annotations

import datetime as dt

from netflix_narc.sync.models import (
    DossierSyncItem,
    SettingsSyncItem,
    SyncBundle,
    ensure_utc,
)


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
            if ensure_utc(remote_item.updated_at) >= ensure_utc(local_item.updated_at):
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

        if ensure_utc(remote_settings.updated_at) >= ensure_utc(local_settings.updated_at):
            return remote_settings
        return local_settings

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

        return SyncBundle(
            version=max(local_bundle.version, remote_bundle.version),
            client_id=local_bundle.client_id,
            timestamp=dt.datetime.now(dt.UTC),
            settings=merged_settings,
            evidence_locker=merged_dossiers,
        )
