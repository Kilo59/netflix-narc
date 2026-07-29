"""Unit tests for storage & sync Pydantic models."""

from __future__ import annotations

import datetime as dt

import pytest

from netflix_narc.sync.models import DossierSyncItem, SettingsSyncItem, SyncBundle, SyncManifest


def test_dossier_sync_item_serialization() -> None:
    """Test DossierSyncItem serialization and default timestamp generation."""
    item = DossierSyncItem(
        title="Breaking Bad",
        content_rating="18",
        user_rating=4.5,
        flagged_for_followup=True,
        category_scores={"violence": 5.0, "language": 4.0},
    )
    dumped = item.model_dump(mode="json")
    assert dumped["title"] == "Breaking Bad"
    assert dumped["content_rating"] == "18"
    assert dumped["user_rating"] == 4.5
    assert dumped["flagged_for_followup"] is True
    assert dumped["category_scores"] == {"violence": 5.0, "language": 4.0}
    assert "updated_at" in dumped

    reloaded = DossierSyncItem.model_validate(dumped)
    assert reloaded.title == item.title
    assert reloaded.user_rating == item.user_rating


def test_settings_sync_item_serialization() -> None:
    """Test SettingsSyncItem serialization."""
    item = SettingsSyncItem(
        active_rating_provider="omdb",
        scoring_mode="balanced",
        child_age_range=(10, 15),
        max_age_rating=16,
        min_quality_rating=3,
        category_weights={"violence": 4, "sexy_stuff": 3},
    )
    dumped = item.model_dump(mode="json")
    assert dumped["active_rating_provider"] == "omdb"
    assert dumped["child_age_range"] == [10, 15]

    reloaded = SettingsSyncItem.model_validate(dumped)
    assert reloaded.child_age_range == (10, 15)
    assert reloaded.category_weights["violence"] == 4


def test_sync_bundle_and_manifest() -> None:
    """Test full SyncBundle assembly and SyncManifest creation."""
    bundle = SyncBundle(
        client_id="test-client-1",
        evidence_locker=[
            DossierSyncItem(title="Inception", content_rating="13"),
        ],
    )
    dumped = bundle.model_dump(mode="json")
    assert dumped["client_id"] == "test-client-1"
    assert len(dumped["evidence_locker"]) == 1

    manifest = SyncManifest(
        latest_bundle_id="bundle.json",
        last_updated=dt.datetime.now(dt.UTC).isoformat(),
        client_id="test-client-1",
    )
    m_dumped = manifest.model_dump(mode="json")
    assert m_dumped["latest_bundle_id"] == "bundle.json"


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
