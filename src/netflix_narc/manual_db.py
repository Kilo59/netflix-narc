"""The Evidence Locker: SQLite storage for manually ingested title data."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import csv
import datetime as dt
import json
import logging
import pathlib
from typing import TYPE_CHECKING, ClassVar, Final

if TYPE_CHECKING:
    from contextlib import AbstractAsyncContextManager

import aiosqlite
from pydantic import BaseModel, ConfigDict, Field, field_validator

from netflix_narc.csm_api import CSMRatingCategory
from netflix_narc.rating_api import NormalizedMetadata
from netflix_narc.sync.models import DossierSyncItem, ensure_utc

logger = logging.getLogger(__name__)

MAX_JSON_LOG_LEN: Final = 200


class ManualMetadata(BaseModel):
    """Extended metadata model for manually ingested titles in The Evidence Locker."""

    model_config: ClassVar[ConfigDict] = {"extra": "forbid"}

    title: str
    content_rating: str | None = None
    user_rating: float | None = None
    image_url: str | None = None
    flagged_for_followup: bool = False
    ignored: bool = False
    category_scores: dict[str, float] = Field(default_factory=dict)
    updated_at: dt.datetime | str = Field(default_factory=lambda: dt.datetime.now(dt.UTC))

    @field_validator("updated_at", mode="before")
    @classmethod
    def _validate_updated_at(cls, v: object) -> dt.datetime:
        return ensure_utc(v)

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
            category_scores TEXT,
            updated_at TEXT
        );
        """
        async with self._get_connection() as db:
            await db.execute(schema)
            # Migration check for existing databases missing updated_at
            try:
                await db.execute("ALTER TABLE evidence_locker ADD COLUMN updated_at TEXT")
            except aiosqlite.OperationalError as exc:
                if "duplicate column name" not in str(exc).lower():
                    raise
            await db.commit()

    def _row_to_manual_metadata(self, row: aiosqlite.Row) -> ManualMetadata:
        """Convert an aiosqlite Row to a ManualMetadata instance."""
        raw_json = row["category_scores"]
        try:
            category_scores = json.loads(raw_json) if raw_json else {}
        except json.JSONDecodeError:
            truncated_raw_json = (
                f"{raw_json[:MAX_JSON_LOG_LEN]}…"
                if raw_json and len(raw_json) > MAX_JSON_LOG_LEN
                else raw_json
            )
            logger.warning(
                "Failed to decode category_scores JSON for title %r: %r",
                row["title"],
                truncated_raw_json,
            )
            category_scores = {}

        row_keys = row.keys()
        updated_at = (
            row["updated_at"]
            if "updated_at" in row_keys and row["updated_at"]
            else dt.datetime.now(dt.UTC).isoformat()
        )

        return ManualMetadata(
            title=row["title"],
            content_rating=row["content_rating"],
            user_rating=row["user_rating"],
            image_url=row["image_url"],
            flagged_for_followup=bool(row["flagged_for_followup"]),
            ignored=bool(row["ignored"]),
            category_scores=category_scores,
            updated_at=updated_at,
        )

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

            return self._row_to_manual_metadata(row)

    async def upsert_record(self, metadata: ManualMetadata) -> None:
        """Insert or update a manual metadata record."""
        async with self._get_connection() as db:
            await db.execute(
                """
                INSERT INTO evidence_locker (
                    title, content_rating, user_rating, image_url,
                    flagged_for_followup, ignored, category_scores, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(title) DO UPDATE SET
                    content_rating=excluded.content_rating,
                    user_rating=excluded.user_rating,
                    image_url=excluded.image_url,
                    flagged_for_followup=excluded.flagged_for_followup,
                    ignored=excluded.ignored,
                    category_scores=excluded.category_scores,
                    updated_at=excluded.updated_at
                """,
                (
                    metadata.title,
                    metadata.content_rating,
                    metadata.user_rating,
                    metadata.image_url,
                    int(metadata.flagged_for_followup),
                    int(metadata.ignored),
                    json.dumps(metadata.category_scores),
                    metadata.updated_at.isoformat()
                    if isinstance(metadata.updated_at, dt.datetime)
                    else str(metadata.updated_at),
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

    async def dump_dossiers(self) -> list[DossierSyncItem]:
        """Dump all evidence locker records as DossierSyncItem objects for sync."""
        records = await self.get_all_records()
        return [
            DossierSyncItem(
                title=r.title,
                content_rating=r.content_rating,
                user_rating=r.user_rating,
                image_url=r.image_url,
                flagged_for_followup=r.flagged_for_followup,
                ignored=r.ignored,
                category_scores=r.category_scores,
                updated_at=r.updated_at,
            )
            for r in records
        ]

    async def get_records_by_titles(self, titles: list[str]) -> dict[str, ManualMetadata]:
        """Fetch multiple records by title in a single batch query."""
        if not titles:
            return {}

        results: dict[str, ManualMetadata] = {}
        chunk_size = 500
        async with self._get_connection() as db:
            db.row_factory = aiosqlite.Row
            for i in range(0, len(titles), chunk_size):
                chunk = titles[i : i + chunk_size]
                placeholders = ",".join("?" for _ in chunk)
                query = f"SELECT * FROM evidence_locker WHERE title IN ({placeholders})"  # noqa: S608
                async with db.execute(query, chunk) as cursor:
                    async for row in cursor:
                        metadata = self._row_to_manual_metadata(row)
                        results[metadata.title] = metadata
        return results

    async def load_dossiers(self, dossiers: list[DossierSyncItem]) -> int:
        """Load and upsert DossierSyncItem objects from sync into evidence locker."""
        if not dossiers:
            return 0

        titles = [item.title for item in dossiers]
        existing_map = await self.get_records_by_titles(titles)

        to_upsert: list[ManualMetadata] = []
        for item in dossiers:
            existing = existing_map.get(item.title)
            if existing is None or ensure_utc(item.updated_at) >= ensure_utc(existing.updated_at):
                to_upsert.append(
                    ManualMetadata(
                        title=item.title,
                        content_rating=item.content_rating,
                        user_rating=item.user_rating,
                        image_url=item.image_url,
                        flagged_for_followup=item.flagged_for_followup,
                        ignored=item.ignored,
                        category_scores=item.category_scores,
                        updated_at=item.updated_at,
                    )
                )

        if not to_upsert:
            return 0

        async with self._get_connection() as db:
            await db.execute("BEGIN IMMEDIATE")
            try:
                for metadata in to_upsert:
                    scores_json = json.dumps(metadata.category_scores)
                    updated_at_str = ensure_utc(metadata.updated_at).isoformat()
                    await db.execute(
                        """
                        INSERT INTO evidence_locker (
                            title, content_rating, user_rating, image_url,
                            flagged_for_followup, ignored, category_scores, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(title) DO UPDATE SET
                            content_rating=excluded.content_rating,
                            user_rating=excluded.user_rating,
                            image_url=excluded.image_url,
                            flagged_for_followup=excluded.flagged_for_followup,
                            ignored=excluded.ignored,
                            category_scores=excluded.category_scores,
                            updated_at=excluded.updated_at;
                        """,
                        (
                            metadata.title,
                            metadata.content_rating,
                            metadata.user_rating,
                            metadata.image_url,
                            int(metadata.flagged_for_followup),
                            int(metadata.ignored),
                            scores_json,
                            updated_at_str,
                        ),
                    )
                await db.commit()
            except Exception:
                await db.rollback()
                raise

        return len(to_upsert)

    async def get_all_records(self) -> list[ManualMetadata]:
        """Retrieve all records for export."""
        async with self._get_connection() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM evidence_locker") as cursor:
                return [self._row_to_manual_metadata(row) async for row in cursor]

    async def export_to_json(self, filepath: pathlib.Path) -> None:
        """Export all manual records to a JSON file."""
        records = [r.model_dump(mode="json") for r in await self.get_all_records()]
        data_str = json.dumps(records, indent=2)
        await asyncio.to_thread(filepath.parent.mkdir, parents=True, exist_ok=True)
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
        await asyncio.to_thread(filepath.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(self._write_csv, filepath, records)

    async def import_from_json(self, filepath: pathlib.Path) -> None:
        """Import records from a JSON file, upserting over existing entries."""
        content = await asyncio.to_thread(filepath.read_text, encoding="utf-8")
        data = json.loads(content)
        for entry in data:
            await self.upsert_record(ManualMetadata(**entry))

    def _read_csv(self, filepath: pathlib.Path) -> list[dict[str, str]]:
        """Synchronously read rows from a CSV file."""
        with filepath.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            return list(reader)

    def _parse_csv_bool(self, val: str | None) -> bool:
        """Safely parse boolean fields from a CSV row, handling empty/malformed inputs."""
        if not val:
            return False
        val_stripped = val.strip().lower()
        if val_stripped in ("1", "true", "yes"):
            return True
        if val_stripped in ("0", "false", "no"):
            return False
        try:
            return bool(int(val_stripped))
        except ValueError:
            return False

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
                flagged_for_followup=self._parse_csv_bool(row.get("flagged_for_followup")),
                ignored=self._parse_csv_bool(row.get("ignored")),
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
