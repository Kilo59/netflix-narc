"""Unit tests for full SyncEngine workflow."""

from __future__ import annotations

import datetime as dt
import pathlib
from typing import override

import pytest

from netflix_narc.manual_db import EvidenceLocker, ManualMetadata
from netflix_narc.persistence import update_env_file
from netflix_narc.settings import ScoringMode, Settings
from netflix_narc.sync.backend import StorageBackendError
from netflix_narc.sync.engine import SyncEngine
from netflix_narc.sync.local_folder import LocalStorageBackend
from netflix_narc.sync.models import SyncBundle, SyncManifest


@pytest.mark.asyncio
async def test_sync_engine_two_client_sync(tmp_path: pathlib.Path) -> None:
    """Simulate two clients (Client A and Client B) syncing data via a shared local folder."""
    shared_sync_dir = tmp_path / "remote_shared_folder"
    client_a_db = tmp_path / "client_a.sqlite"
    client_b_db = tmp_path / "client_b.sqlite"

    locker_a = EvidenceLocker(client_a_db)
    await locker_a.init()

    locker_b = EvidenceLocker(client_b_db)
    await locker_b.init()

    backend_a = LocalStorageBackend(shared_sync_dir)
    backend_b = LocalStorageBackend(shared_sync_dir)

    engine_a = SyncEngine(backend=backend_a, locker=locker_a, client_id="client-a")
    engine_b = SyncEngine(backend=backend_b, locker=locker_b, client_id="client-b")

    # Step 1: Client A adds a record and syncs
    await locker_a.upsert_record(
        ManualMetadata(title="Arcane", content_rating="16", user_rating=5.0)
    )
    result_a = await engine_a.sync()
    assert result_a.status == "success"

    # Step 2: Client B syncs (downloads Client A's record)
    record_b_before = await locker_b.get_record("Arcane")
    assert record_b_before is None

    result_b = await engine_b.sync()
    assert result_b.status == "success"

    record_b_after = await locker_b.get_record("Arcane")
    assert record_b_after is not None
    assert record_b_after.user_rating == 5.0

    # Step 3: Client B adds a new record and syncs back
    await locker_b.upsert_record(
        ManualMetadata(title="Wednesday", content_rating="12", user_rating=4.0)
    )
    await engine_b.sync()

    # Step 4: Client A syncs and receives Wednesday
    await engine_a.sync()
    record_a_wednesday = await locker_a.get_record("Wednesday")
    assert record_a_wednesday is not None
    assert record_a_wednesday.user_rating == 4.0


@pytest.mark.asyncio
async def test_sync_engine_settings_synced_across_devices(tmp_path: pathlib.Path) -> None:
    """Settings updated on Client A should synchronize to Client B's in-memory Settings."""
    shared_sync_dir = tmp_path / "settings_sync_folder"
    env_a = tmp_path / "env_a.env"
    env_b = tmp_path / "env_b.env"

    settings_a = Settings(_env_file=str(env_a))  # type: ignore[call-arg]
    settings_a.child_age_range = (6, 10)
    settings_a.max_age_rating = 14
    settings_a.scoring_mode = ScoringMode.QUALITY_FOCUS

    # Save Client A's settings so env_a has a recent file timestamp
    update_env_file(
        provider=settings_a.active_rating_provider,
        api_key=settings_a.omdb_api_key,
        env_path=env_a,
        child_age_range=settings_a.child_age_range,
        extra_env={"SCORING_MODE": str(settings_a.scoring_mode), "MAX_AGE_RATING": "14"},
    )

    settings_b = Settings(_env_file=str(env_b))  # type: ignore[call-arg]

    locker_a = EvidenceLocker(tmp_path / "a.sqlite")
    await locker_a.init()
    locker_b = EvidenceLocker(tmp_path / "b.sqlite")
    await locker_b.init()

    backend_a = LocalStorageBackend(shared_sync_dir)
    backend_b = LocalStorageBackend(shared_sync_dir)

    engine_a = SyncEngine(backend=backend_a, locker=locker_a, settings=settings_a, client_id="a")
    engine_b = SyncEngine(backend=backend_b, locker=locker_b, settings=settings_b, client_id="b")

    # Client A syncs settings
    res_a = await engine_a.sync()
    assert res_a.status == "success"

    # Client B syncs and receives Client A's updated settings
    res_b = await engine_b.sync()
    assert res_b.status == "success"

    assert settings_b.child_age_range == (6, 10)
    assert settings_b.max_age_rating == 14
    assert settings_b.scoring_mode == ScoringMode.QUALITY_FOCUS


@pytest.mark.asyncio
async def test_sync_engine_initial_upload_when_no_remote_bundle(tmp_path: pathlib.Path) -> None:
    """Test SyncEngine handles missing remote bundle by uploading local state."""
    sync_dir = tmp_path / "empty_remote"
    db_path = tmp_path / "client.sqlite"

    locker = EvidenceLocker(db_path)
    await locker.init()
    await locker.upsert_record(ManualMetadata(title="Dark", content_rating="16"))

    backend = LocalStorageBackend(sync_dir)
    engine = SyncEngine(backend=backend, locker=locker, client_id="initial-client")

    res = await engine.sync()
    assert res.status == "success"
    assert res.items_synced >= 1
    assert "Uploaded initial local bundle" in res.message or "Uploaded" in res.message


@pytest.mark.asyncio
async def test_sync_engine_handles_storage_backend_error(tmp_path: pathlib.Path) -> None:
    """Test SyncEngine returns error status on StorageBackendError."""

    class FailingBackend(LocalStorageBackend):
        @override
        async def download_bundle(self) -> SyncBundle | None:
            err_msg = "Network unreachable"
            raise StorageBackendError(err_msg)

        @override
        async def get_manifest(self) -> SyncManifest | None:
            return SyncManifest(
                latest_bundle_id="remote.json",
                last_updated=dt.datetime(2026, 1, 1, 0, 0, 0, tzinfo=dt.UTC),
                client_id="other",
            )

    db_path = tmp_path / "client.sqlite"
    locker = EvidenceLocker(db_path)
    await locker.init()

    failing_backend = FailingBackend(tmp_path / "sync")
    engine = SyncEngine(backend=failing_backend, locker=locker, client_id="fail-client")

    res = await engine.sync()
    assert res.status == "error"
    assert res.items_synced == 0
    assert "Network unreachable" in res.message


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
