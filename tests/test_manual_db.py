"""Tests for the Evidence Locker (manual_db.py)."""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pathlib

import aiosqlite
import pytest
import pytest_asyncio

from netflix_narc.manual_db import EvidenceLocker, ManualMetadata
from netflix_narc.sync.models import DossierSyncItem


@pytest_asyncio.fixture
async def temp_db(tmp_path: pathlib.Path) -> EvidenceLocker:
    """Provide a fresh EvidenceLocker instance in a temporary directory."""
    db_file = tmp_path / "test_evidence.sqlite"
    locker = EvidenceLocker(db_file)
    await locker.init()
    return locker


@pytest.mark.asyncio
async def test_upsert_and_get_record(temp_db: EvidenceLocker) -> None:
    """Test inserting and retrieving a manual metadata record."""
    metadata = ManualMetadata(
        title="Breaking Bad",
        content_rating="18",
        user_rating=5.0,
        image_url="http://example.com/image.jpg",
        flagged_for_followup=True,
        ignored=False,
        category_scores={
            "Violence & Scariness": 4.5,
            "Language": 5.0,
        },
    )

    await temp_db.upsert_record(metadata)
    record = await temp_db.get_record("Breaking Bad")

    assert record is not None
    assert record.title == "Breaking Bad"
    assert record.content_rating == "18"
    assert record.user_rating == 5.0
    assert record.image_url == "http://example.com/image.jpg"
    assert record.flagged_for_followup is True
    assert record.ignored is False
    assert record.category_scores == {"Violence & Scariness": 4.5, "Language": 5.0}

    # Test update
    metadata.user_rating = 4.0
    await temp_db.upsert_record(metadata)
    record2 = await temp_db.get_record("Breaking Bad")
    assert record2 is not None
    assert record2.user_rating == 4.0


@pytest.mark.asyncio
async def test_get_nonexistent_record(temp_db: EvidenceLocker) -> None:
    """Test retrieving a title that doesn't exist."""
    assert await temp_db.get_record("Nonexistent Title") is None


@pytest.mark.asyncio
async def test_ignore_title(temp_db: EvidenceLocker) -> None:
    """Test the convenience method for ignoring a title."""
    await temp_db.ignore_title("Boring Show")
    record = await temp_db.get_record("Boring Show")
    assert record is not None
    assert record.title == "Boring Show"
    assert record.ignored is True

    # Check ignoring an existing record doesn't wipe other fields
    metadata = ManualMetadata(title="Existing Show", content_rating="PG")
    await temp_db.upsert_record(metadata)
    await temp_db.ignore_title("Existing Show")
    record2 = await temp_db.get_record("Existing Show")
    assert record2 is not None
    assert record2.ignored is True
    assert record2.content_rating == "PG"


@pytest.mark.asyncio
async def test_export_import_json(temp_db: EvidenceLocker, tmp_path: pathlib.Path) -> None:
    """Test JSON export and import."""
    metadata = ManualMetadata(title="JSON Show", user_rating=4.2)
    await temp_db.upsert_record(metadata)

    json_file = tmp_path / "export.json"
    await temp_db.export_to_json(json_file)

    assert json_file.exists()

    # Create a new db and import
    db2 = EvidenceLocker(tmp_path / "db2.sqlite")
    await db2.init()
    await db2.import_from_json(json_file)
    record = await db2.get_record("JSON Show")
    assert record is not None
    assert record.user_rating == 4.2


@pytest.mark.asyncio
async def test_export_import_csv(temp_db: EvidenceLocker, tmp_path: pathlib.Path) -> None:
    """Test CSV export and import."""
    metadata = ManualMetadata(
        title="CSV Show",
        content_rating="PG-13",
        user_rating=3.5,
        flagged_for_followup=True,
        category_scores={"Violence & Scariness": 3.0, "Language": 1.0},
    )
    await temp_db.upsert_record(metadata)

    csv_file = tmp_path / "export.csv"
    await temp_db.export_to_csv(csv_file)

    assert csv_file.exists()

    # Create a new db and import
    db2 = EvidenceLocker(tmp_path / "db3.sqlite")
    await db2.init()
    await db2.import_from_csv(csv_file)
    record = await db2.get_record("CSV Show")
    assert record is not None
    assert record.title == "CSV Show"
    assert record.content_rating == "PG-13"
    assert record.user_rating == 3.5
    assert record.flagged_for_followup is True
    assert record.category_scores["Violence & Scariness"] == 3.0
    assert record.category_scores["Language"] == 1.0


def test_manual_metadata_normalization_scaling() -> None:
    """Verify that user_rating remains raw (1.0-5.0) in ManualMetadata.

    It should be doubled strictly in to_normalized_metadata().
    """
    metadata = ManualMetadata(
        title="Test Scaling",
        user_rating=4.5,
        category_scores={"Violence & Scariness": 3.0},
    )
    assert metadata.user_rating == 4.5

    normalized = metadata.to_normalized_metadata()
    assert normalized.user_rating == 9.0
    assert normalized.category_scores == {"Violence & Scariness": 3.0}


@pytest.mark.asyncio
async def test_corrupt_category_scores_json_logging(
    temp_db: EvidenceLocker, caplog: pytest.LogCaptureFixture
) -> None:
    """Verify that malformed JSON in category_scores logs a warning."""
    title = "Corrupt Show"
    # Insert corrupt raw data directly into the DB using connection
    async with aiosqlite.connect(temp_db.db_path) as db:
        await db.execute(
            "INSERT INTO evidence_locker (title, category_scores) VALUES (?, ?)",
            (title, "{corrupt-json"),
        )
        await db.commit()

    with caplog.at_level("WARNING"):
        record = await temp_db.get_record(title)

    assert record is not None
    assert record.category_scores == {}
    assert any(
        "Failed to decode category_scores JSON for title" in record.message
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_import_csv_robust_bool_parsing(
    temp_db: EvidenceLocker, tmp_path: pathlib.Path
) -> None:
    """Verify that malformed or empty boolean CSV cells are safely handled."""
    csv_content = (
        "title,content_rating,user_rating,image_url,flagged_for_followup,ignored\n"
        "Show A,PG,4.0,,yes,no\n"
        "Show B,R,5.0,,1,\n"  # empty ignored is False
        "Show C,G,3.0,,malformed_value,2\n"  # malformed defaults to False, 2 is True
    )
    csv_file = tmp_path / "robust_bools.csv"
    csv_file.write_text(csv_content, encoding="utf-8")

    await temp_db.import_from_csv(csv_file)

    record_a = await temp_db.get_record("Show A")
    assert record_a is not None
    assert record_a.flagged_for_followup is True
    assert record_a.ignored is False

    record_b = await temp_db.get_record("Show B")
    assert record_b is not None
    assert record_b.flagged_for_followup is True
    assert record_b.ignored is False

    record_c = await temp_db.get_record("Show C")
    assert record_c is not None
    assert record_c.flagged_for_followup is False  # malformed defaults to False
    assert record_c.ignored is True  # "2" evaluates to True


@pytest.mark.asyncio
async def test_exports_create_parent_directory(
    temp_db: EvidenceLocker, tmp_path: pathlib.Path
) -> None:
    """Verify that exports successfully create missing parent directories."""
    metadata = ManualMetadata(title="Export Test Show")
    await temp_db.upsert_record(metadata)

    export_dir = tmp_path / "new_parent_dir"
    json_file = export_dir / "subdir" / "export.json"
    csv_file = export_dir / "subdir" / "export.csv"

    assert not export_dir.exists()

    await temp_db.export_to_json(json_file)
    assert json_file.exists()

    await temp_db.export_to_csv(csv_file)
    assert csv_file.exists()


@pytest.mark.asyncio
async def test_dump_and_load_dossiers(temp_db: EvidenceLocker) -> None:
    """Test dump_dossiers and load_dossiers sync helper methods."""
    await temp_db.upsert_record(
        ManualMetadata(title="Show X", content_rating="16", user_rating=4.5)
    )

    dossiers = await temp_db.dump_dossiers()
    assert len(dossiers) == 1
    assert dossiers[0].title == "Show X"
    assert dossiers[0].user_rating == 4.5
    assert dossiers[0].updated_at is not None

    # Load into another empty DB
    db2_file = temp_db.db_path.parent / "db_dump_load.sqlite"
    db2 = EvidenceLocker(db2_file)
    await db2.init()

    loaded_count = await db2.load_dossiers(dossiers)
    assert loaded_count == 1
    rec2 = await db2.get_record("Show X")
    assert rec2 is not None
    assert rec2.user_rating == 4.5


@pytest.mark.asyncio
async def test_load_dossiers_lww_newer_incoming_overwrites(temp_db: EvidenceLocker) -> None:
    """load_dossiers should overwrite local record when incoming updated_at is newer."""
    old_time = dt.datetime(2026, 1, 1, 12, 0, 0, tzinfo=dt.UTC)
    new_time = dt.datetime(2026, 1, 2, 12, 0, 0, tzinfo=dt.UTC)

    await temp_db.upsert_record(
        ManualMetadata(title="LWW Show", user_rating=3.0, updated_at=old_time)
    )

    incoming = [DossierSyncItem(title="LWW Show", user_rating=5.0, updated_at=new_time)]
    updated_count = await temp_db.load_dossiers(incoming)
    assert updated_count == 1

    record = await temp_db.get_record("LWW Show")
    assert record is not None
    assert record.user_rating == 5.0


@pytest.mark.asyncio
async def test_load_dossiers_lww_older_incoming_ignored(temp_db: EvidenceLocker) -> None:
    """load_dossiers should NOT overwrite local record when incoming updated_at is older."""
    new_time = dt.datetime(2026, 1, 2, 12, 0, 0, tzinfo=dt.UTC)
    old_time = dt.datetime(2026, 1, 1, 12, 0, 0, tzinfo=dt.UTC)

    await temp_db.upsert_record(
        ManualMetadata(title="LWW Show", user_rating=5.0, updated_at=new_time)
    )

    incoming = [DossierSyncItem(title="LWW Show", user_rating=1.0, updated_at=old_time)]
    updated_count = await temp_db.load_dossiers(incoming)
    assert updated_count == 0

    record = await temp_db.get_record("LWW Show")
    assert record is not None
    assert record.user_rating == 5.0


@pytest.mark.asyncio
async def test_db_migration_backfills_updated_at(tmp_path: pathlib.Path) -> None:
    """Test initializing an older database schema without updated_at column."""
    db_file = tmp_path / "legacy.sqlite"
    async with aiosqlite.connect(db_file) as db:
        await db.execute(
            """
            CREATE TABLE evidence_locker (
                title TEXT PRIMARY KEY,
                content_rating TEXT,
                user_rating REAL,
                image_url TEXT,
                flagged_for_followup INTEGER DEFAULT 0,
                ignored INTEGER DEFAULT 0,
                category_scores TEXT
            );
            """
        )
        await db.execute("INSERT INTO evidence_locker (title) VALUES ('Legacy Show')")
        await db.commit()

    locker = EvidenceLocker(db_file)
    await locker.init()  # Triggers migration check

    record = await locker.get_record("Legacy Show")
    assert record is not None
    assert record.title == "Legacy Show"
    assert record.updated_at is not None


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
