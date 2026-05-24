"""Tests for the Evidence Locker (manual_db.py)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pathlib

import pytest
import pytest_asyncio

from netflix_narc.manual_db import EvidenceLocker, ManualMetadata


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
    assert record.user_rating == 5.0  # noqa: PLR2004
    assert record.image_url == "http://example.com/image.jpg"
    assert record.flagged_for_followup is True
    assert record.ignored is False
    assert record.category_scores == {"Violence & Scariness": 4.5, "Language": 5.0}

    # Test update
    metadata.user_rating = 4.0
    await temp_db.upsert_record(metadata)
    record2 = await temp_db.get_record("Breaking Bad")
    assert record2 is not None
    assert record2.user_rating == 4.0  # noqa: PLR2004


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
    assert record.user_rating == 4.2  # noqa: PLR2004


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
    assert record.user_rating == 3.5  # noqa: PLR2004
    assert record.flagged_for_followup is True
    assert record.category_scores["Violence & Scariness"] == 3.0  # noqa: PLR2004
    assert record.category_scores["Language"] == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
