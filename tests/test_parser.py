from datetime import datetime
from pathlib import Path

import pytest

from netflix_narc.parser import parse_netflix_history


def test_parse_netflix_history_valid_data(tmp_path: Path):
    """Test parsing a valid Netflix history CSV file."""
    csv_file = tmp_path / "ViewingHistory.csv"
    csv_file.write_text(
        "Title,Date\n"
        '"Peppa Pig: Season 3: The Camping Holiday","1/3/26"\n'
        '"Spider-Man: Into the Spider-Verse","12/31/25"\n',
        encoding="utf-8",
    )

    records = parse_netflix_history(csv_file)

    assert len(records) == 2
    assert records[0].title == "Peppa Pig: Season 3: The Camping Holiday"
    assert records[0].date_watched == datetime(2026, 1, 3)

    assert records[1].title == "Spider-Man: Into the Spider-Verse"
    assert records[1].date_watched == datetime(2025, 12, 31)


def test_parse_netflix_history_missing_fields(tmp_path: Path):
    """Test parsing a CSV with missing fields in some rows."""
    csv_file = tmp_path / "ViewingHistory.csv"
    csv_file.write_text(
        'Title,Date\n"Peppa Pig: Season 3","1/3/26"\n"Missing Date",\n,"1/2/26"\n', encoding="utf-8"
    )

    records = parse_netflix_history(csv_file)

    # Only one valid row should be parsed
    assert len(records) == 1
    assert records[0].title == "Peppa Pig: Season 3"


def test_parse_netflix_history_invalid_date_format(tmp_path: Path):
    """Test parsing a CSV with an invalid date formatRaises ValueError."""
    csv_file = tmp_path / "ViewingHistory.csv"
    csv_file.write_text('Title,Date\n"Bad Date Format","2026-01-03"\n', encoding="utf-8")

    with pytest.raises(ValueError, match="Failed to parse row"):
        parse_netflix_history(csv_file)


def test_parse_netflix_history_file_not_found():
    """Test parsing a non-existent file."""
    with pytest.raises(FileNotFoundError):
        parse_netflix_history(Path("does_not_exist.csv"))
