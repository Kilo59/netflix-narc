"""Unit tests for full SyncEngine workflow."""

from __future__ import annotations

import pathlib

import pytest

from netflix_narc.manual_db import EvidenceLocker, ManualMetadata
from netflix_narc.sync.engine import SyncEngine
from netflix_narc.sync.local_folder import LocalStorageBackend


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
    assert record_b_after is None or record_b_after is not None
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


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
