"""The Evidence Locker: SQLite storage for manually ingested title data."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import csv
import json
import logging
import pathlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from contextlib import AbstractAsyncContextManager

import aiosqlite
from pydantic import BaseModel, Field

from netflix_narc.csm_api import CSMRatingCategory
from netflix_narc.rating_api import NormalizedMetadata

logger = logging.getLogger(__name__)


class ManualMetadata(BaseModel):
    """Extended metadata model for manually ingested titles in The Evidence Locker."""

    title: str
    content_rating: str | None = None
    user_rating: float | None = None
    image_url: str | None = None
    flagged_for_followup: bool = False
    ignored: bool = False
    category_scores: dict[str, float] = Field(default_factory=dict)

    @property
    def completeness_score(self) -> int:
        """Calculate a 0-100 completeness score for the dossier.

        The score is based on content_rating, user_rating, image_url,
        plus one field for each CSMRatingCategory entry (from category_scores).
        """
        # 3 fixed fields: content_rating, user_rating, image_url
        total_fields = 3 + len(CSMRatingCategory)

        if total_fields == 0:
            return 0

        filled = 0

        if self.content_rating is not None:
            filled += 1
        if self.user_rating is not None:
            filled += 1
        if self.image_url is not None:
            filled += 1

        for cat in CSMRatingCategory:
            if cat.value in self.category_scores:
                filled += 1

        return round(100 * filled / total_fields)

    def to_normalized_metadata(self) -> NormalizedMetadata:
        """Convert to standard NormalizedMetadata."""
        return NormalizedMetadata(
            title=self.title,
            content_rating=self.content_rating,
            user_rating=(self.user_rating * 2.0) if self.user_rating is not None else None,
            provider_name="manual",
            category_scores=self.category_scores,
        )


class EvidenceLocker:
    """SQLite wrapper for the manual data ingestion persistent storage."""

    def __init__(self, db_path: pathlib.Path | str = "evidence_locker.sqlite") -> None:
        """Initialize the Evidence Locker SQLite database."""
        self.db_path = pathlib.Path(db_path)

    def _get_connection(self) -> AbstractAsyncContextManager[aiosqlite.Connection]:
        """Return an async context manager yielding an aiosqlite connection."""
        return aiosqlite.connect(self.db_path)

    async def init(self) -> None:
        """Create the schema if it doesn't exist. Must be called after instantiation."""
        # Using a JSON column for category_scores allows easy mapping of categories
        schema = """
        CREATE TABLE IF NOT EXISTS evidence_locker (
            title TEXT PRIMARY KEY,
            content_rating TEXT,
            user_rating REAL,
            image_url TEXT,
            flagged_for_followup INTEGER DEFAULT 0,
            ignored INTEGER DEFAULT 0,
            category_scores TEXT
        );
        """
        async with self._get_connection() as db:
            await db.execute(schema)
            await db.commit()

    async def get_record(self, title: str) -> ManualMetadata | None:
        """Fetch a specific title's manual metadata from the Evidence Locker."""
        async with self._get_connection() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM evidence_locker WHERE title = ?", (title,)
            ) as cursor:
                row = await cursor.fetchone()

            if not row:
                return None

            try:
                raw_json = row["category_scores"]
                category_scores = json.loads(raw_json) if raw_json else {}
            except json.JSONDecodeError:
                category_scores = {}

            return ManualMetadata(
                title=row["title"],
                content_rating=row["content_rating"],
                user_rating=row["user_rating"],
                image_url=row["image_url"],
                flagged_for_followup=bool(row["flagged_for_followup"]),
                ignored=bool(row["ignored"]),
                category_scores=category_scores,
            )

    async def upsert_record(self, metadata: ManualMetadata) -> None:
        """Insert or update a manual metadata record."""
        async with self._get_connection() as db:
            await db.execute(
                """
                INSERT INTO evidence_locker (
                    title, content_rating, user_rating, image_url,
                    flagged_for_followup, ignored, category_scores
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(title) DO UPDATE SET
                    content_rating=excluded.content_rating,
                    user_rating=excluded.user_rating,
                    image_url=excluded.image_url,
                    flagged_for_followup=excluded.flagged_for_followup,
                    ignored=excluded.ignored,
                    category_scores=excluded.category_scores
                """,
                (
                    metadata.title,
                    metadata.content_rating,
                    metadata.user_rating,
                    metadata.image_url,
                    int(metadata.flagged_for_followup),
                    int(metadata.ignored),
                    json.dumps(metadata.category_scores),
                ),
            )
            await db.commit()

    async def ignore_title(self, title: str) -> None:
        """Convenience method to permanently ignore a title without filling out metadata."""
        record = await self.get_record(title)
        if record:
            record.ignored = True
        else:
            record = ManualMetadata(title=title, ignored=True)
        await self.upsert_record(record)

    async def get_all_records(self) -> list[ManualMetadata]:
        """Retrieve all records for export."""
        records = []
        async with self._get_connection() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM evidence_locker") as cursor:
                async for row in cursor:
                    try:
                        raw_cat = row["category_scores"]
                        scores = json.loads(raw_cat) if raw_cat else {}
                    except json.JSONDecodeError:
                        scores = {}

                    records.append(
                        ManualMetadata(
                            title=row["title"],
                            content_rating=row["content_rating"],
                            user_rating=row["user_rating"],
                            image_url=row["image_url"],
                            flagged_for_followup=bool(row["flagged_for_followup"]),
                            ignored=bool(row["ignored"]),
                            category_scores=scores,
                        )
                    )
        return records

    async def export_to_json(self, filepath: pathlib.Path) -> None:
        """Export all manual records to a JSON file."""
        records = [r.model_dump() for r in await self.get_all_records()]
        data_str = json.dumps(records, indent=2)
        await asyncio.to_thread(filepath.write_text, data_str, encoding="utf-8")

    def _write_csv(self, filepath: pathlib.Path, records: list[ManualMetadata]) -> None:
        """Synchronously write records to a CSV file."""
        fieldnames = [
            "title",
            "content_rating",
            "user_rating",
            "image_url",
            "flagged_for_followup",
            "ignored",
        ]
        fieldnames.extend(category.value for category in CSMRatingCategory)

        with filepath.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for record in records:
                row = {
                    "title": record.title,
                    "content_rating": record.content_rating,
                    "user_rating": record.user_rating,
                    "image_url": record.image_url,
                    "flagged_for_followup": int(record.flagged_for_followup),
                    "ignored": int(record.ignored),
                }
                for category in CSMRatingCategory:
                    row[category.value] = record.category_scores.get(category.value, "")
                writer.writerow(row)

    async def export_to_csv(self, filepath: pathlib.Path) -> None:
        """Export all manual records to a CSV file."""
        records = await self.get_all_records()
        if not records:
            return
        await asyncio.to_thread(self._write_csv, filepath, records)

    async def import_from_json(self, filepath: pathlib.Path) -> None:
        """Import records from a JSON file, upserting over existing entries."""
        content = await asyncio.to_thread(filepath.read_text, encoding="utf-8")
        data = json.loads(content)
        for entry in data:
            await self.upsert_record(ManualMetadata(**entry))

    def _read_csv(self, filepath: pathlib.Path) -> list[dict[str, str]]:
        """Synchronously read rows from a CSV file."""
        with filepath.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)

    async def import_from_csv(self, filepath: pathlib.Path) -> None:
        """Import records from a CSV file, upserting over existing entries."""
        rows = await asyncio.to_thread(self._read_csv, filepath)
        for row in rows:
            scores = {}
            for category in CSMRatingCategory:
                val = row.get(category.value)
                if val:
                    with contextlib.suppress(ValueError):
                        scores[category.value] = float(val)

            metadata = ManualMetadata(
                title=row["title"],
                content_rating=row.get("content_rating") or None,
                user_rating=float(row["user_rating"]) if row.get("user_rating") else None,
                image_url=row.get("image_url") or None,
                flagged_for_followup=bool(int(row.get("flagged_for_followup", 0))),
                ignored=bool(int(row.get("ignored", 0))),
                category_scores=scores,
            )
            await self.upsert_record(metadata)


# CLI interface for import/export tools
async def main() -> None:
    """CLI entrypoint for managing the Evidence Locker."""
    parser = argparse.ArgumentParser(description="Evidence Locker DB Utilities")
    parser.add_argument("action", choices=["export", "import"])
    parser.add_argument("format", choices=["json", "csv"])
    parser.add_argument("filepath", type=pathlib.Path)
    parser.add_argument("--db", default="evidence_locker.sqlite", type=pathlib.Path)

    args = parser.parse_args()

    locker = EvidenceLocker(args.db)
    await locker.init()

    if args.action == "export":
        if args.format == "json":
            await locker.export_to_json(args.filepath)
        else:
            await locker.export_to_csv(args.filepath)
        print(f"Exported evidence to {args.filepath}")  # noqa: T201
    elif args.action == "import":
        if args.format == "json":
            await locker.import_from_json(args.filepath)
        else:
            await locker.import_from_csv(args.filepath)
        print(f"Imported evidence from {args.filepath}")  # noqa: T201


if __name__ == "__main__":
    asyncio.run(main())
