"""Utility for parsing Netflix viewing history CSV files."""

from __future__ import annotations

import csv
import datetime as dt
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    import pathlib


class ViewingRecord(BaseModel):
    """Represents a single viewing event from the Netflix history export."""

    title: str = Field(description="The full title of the show or movie watched.")
    date_watched: dt.datetime = Field(description="The date the title was watched.")

    model_config = ConfigDict(frozen=True)


def parse_netflix_history(csv_path: pathlib.Path) -> list[ViewingRecord]:
    """Parse a Netflix ViewingHistory.csv file into a list of ViewingRecords.

    Args:
        csv_path: The path to the CSV file.

    Returns:
        A list of parsed ViewingRecords.

    Raises:
        FileNotFoundError: If the CSV file does not exist.
        ValueError: If a row cannot be parsed correctly.
    """
    records: list[ViewingRecord] = []

    with csv_path.open(encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            raw_title = row.get("Title")
            raw_date = row.get("Date")

            if not raw_title or not raw_date:
                continue

            try:
                # The provided CSV uses '%m/%d/%y' format (e.g., '1/3/26')
                parsed_date = dt.datetime.strptime(raw_date, "%m/%d/%y").replace(tzinfo=dt.UTC)

                # Netflix often formats titles as "Series Name: Season X: Episode Title"
                # We retain the full string here; the CSM API integration may need to strip this
                # down to just the Series Name later for searching.
                record = ViewingRecord(title=raw_title, date_watched=parsed_date)
                records.append(record)
            except ValueError as e:
                # If date parsing fails, we could log it or raise.
                # For this implementation, we will log a warning or raise depending on strictness.
                # Here we raise to ensure data integrity during development.
                msg = f"Failed to parse row: {row}. Error: {e}"
                raise ValueError(msg) from e

    return records
