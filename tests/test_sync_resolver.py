"""Unit tests for conflict resolution engine."""

from __future__ import annotations

import datetime as dt

import pytest

from netflix_narc.sync.models import DossierSyncItem, SettingsSyncItem, SyncBundle
from netflix_narc.sync.resolver import ConflictResolver


def test_conflict_resolver_dossier_lww() -> None:
    """Test Last-Write-Wins (LWW) per-title dossier merging."""
    resolver = ConflictResolver()

    t_old = dt.datetime(2026, 1, 1, 12, 0, 0, tzinfo=dt.UTC).isoformat()
    t_new = dt.datetime(2026, 1, 2, 12, 0, 0, tzinfo=dt.UTC).isoformat()

    local_items = [
        DossierSyncItem(title="Item A", user_rating=3.0, updated_at=t_old),
        DossierSyncItem(title="Item B", user_rating=4.0, updated_at=t_new),
    ]

    remote_items = [
        DossierSyncItem(title="Item A", user_rating=5.0, updated_at=t_new),  # Remote is newer
        DossierSyncItem(title="Item B", user_rating=2.0, updated_at=t_old),  # Local is newer
        DossierSyncItem(title="Item C", user_rating=4.5, updated_at=t_old),  # Remote only
    ]

    merged = resolver.merge_dossiers(local_items, remote_items)
    merged_map = {item.title: item for item in merged}

    assert len(merged) == 3
    assert merged_map["Item A"].user_rating == 5.0  # Remote won
    assert merged_map["Item B"].user_rating == 4.0  # Local won
    assert merged_map["Item C"].user_rating == 4.5  # Added remote only item


def test_conflict_resolver_settings_lww() -> None:
    """Test Last-Write-Wins settings merging."""
    resolver = ConflictResolver()

    t_old = dt.datetime(2026, 1, 1, 10, 0, 0, tzinfo=dt.UTC).isoformat()
    t_new = dt.datetime(2026, 1, 2, 10, 0, 0, tzinfo=dt.UTC).isoformat()

    s_local = SettingsSyncItem(
        active_rating_provider="csm",
        scoring_mode="balanced",
        max_age_rating=12,
        min_quality_rating=3,
        updated_at=t_old,
    )
    s_remote = SettingsSyncItem(
        active_rating_provider="omdb",
        scoring_mode="quality_focus",
        max_age_rating=16,
        min_quality_rating=4,
        updated_at=t_new,
    )

    resolved = resolver.merge_settings(s_local, s_remote)
    assert resolved is not None
    assert resolved.active_rating_provider == "omdb"
    assert resolved.max_age_rating == 16


def test_conflict_resolver_bundle_merge() -> None:
    """Test merging full SyncBundles."""
    resolver = ConflictResolver()

    t_now = dt.datetime.now(dt.UTC).isoformat()
    b_local = SyncBundle(
        client_id="client-a",
        timestamp=t_now,
        evidence_locker=[DossierSyncItem(title="Title 1", user_rating=3.5)],
    )
    b_remote = SyncBundle(
        client_id="client-b",
        timestamp=t_now,
        evidence_locker=[DossierSyncItem(title="Title 2", user_rating=4.5)],
    )

    merged = resolver.merge_bundles(b_local, b_remote)
    assert len(merged.evidence_locker) == 2
    assert merged.client_id == "client-a"


def test_conflict_resolver_dossier_lww_invalid_updated_at_favors_valid() -> None:
    """Malformed or empty updated_at should lose against a valid timestamp (LWW)."""
    resolver = ConflictResolver()

    valid_ts = dt.datetime(2026, 1, 2, 12, 0, 0, tzinfo=dt.UTC)
    invalid_ts = "not-a-timestamp"
    empty_ts = ""

    local_items = [
        DossierSyncItem(title="Item A", user_rating=1.0, updated_at=invalid_ts),
        DossierSyncItem(title="Item B", user_rating=2.0, updated_at=empty_ts),
    ]
    remote_items = [
        DossierSyncItem(title="Item A", user_rating=3.0, updated_at=valid_ts),
        DossierSyncItem(title="Item B", user_rating=4.0, updated_at=valid_ts),
    ]

    merged = resolver.merge_dossiers(local_items, remote_items)
    merged_map = {item.title: item for item in merged}

    assert merged_map["Item A"].user_rating == 3.0
    assert merged_map["Item B"].user_rating == 4.0


def test_conflict_resolver_dossier_lww_naive_timestamps_treated_as_utc() -> None:
    """Naive datetime strings should be interpreted as UTC for LWW decisions."""
    resolver = ConflictResolver()

    naive_ts = "2026-01-02T12:00:00"
    utc_ts = dt.datetime(2026, 1, 2, 12, 0, 0, tzinfo=dt.UTC)

    local_items = [
        DossierSyncItem(title="Item A", user_rating=1.0, updated_at=naive_ts),
    ]
    remote_items = [
        DossierSyncItem(title="Item A", user_rating=2.0, updated_at=utc_ts),
    ]

    merged = resolver.merge_dossiers(local_items, remote_items)
    assert len(merged) == 1
    assert merged[0].user_rating == 2.0


def test_conflict_resolver_settings_lww_with_invalid_timestamps() -> None:
    """merge_settings should yield deterministic LWW behavior with invalid timestamps."""
    resolver = ConflictResolver()

    valid_ts = dt.datetime(2026, 1, 3, 12, 0, 0, tzinfo=dt.UTC)
    malformed_ts = "2026-13-40T25:61:61Z"

    s_local = SettingsSyncItem(
        active_rating_provider="csm",
        scoring_mode="balanced",
        max_age_rating=12,
        min_quality_rating=3,
        updated_at=malformed_ts,
    )
    s_remote = SettingsSyncItem(
        active_rating_provider="omdb",
        scoring_mode="quality_focus",
        max_age_rating=16,
        min_quality_rating=4,
        updated_at=valid_ts,
    )

    resolved = resolver.merge_settings(s_local, s_remote)
    assert resolved is not None
    assert resolved.active_rating_provider == "omdb"


def test_conflict_resolver_exact_timestamp_tie_prefers_remote() -> None:
    """On exact timestamp ties, remote side should win (remote.updated_at >= local.updated_at)."""
    resolver = ConflictResolver()

    ts = dt.datetime(2026, 1, 2, 12, 0, 0, tzinfo=dt.UTC)

    local_items = [DossierSyncItem(title="Tie Item", user_rating=3.0, updated_at=ts)]
    remote_items = [DossierSyncItem(title="Tie Item", user_rating=4.5, updated_at=ts)]

    merged = resolver.merge_dossiers(local_items, remote_items)
    assert len(merged) == 1
    assert merged[0].user_rating == 4.5


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
