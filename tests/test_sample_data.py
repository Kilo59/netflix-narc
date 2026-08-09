"""Tests for sample_data module."""

from __future__ import annotations

import pytest

from netflix_narc.manual_db import ManualMetadata
from netflix_narc.sample_data import SAMPLE_MANUAL_RECORDS, get_sample_manual_records


def test_get_sample_manual_records() -> None:
    """Ensure sample records are valid ManualMetadata instances and deep copies are returned."""
    records = get_sample_manual_records()
    assert len(records) > 0
    for record in records:
        assert isinstance(record, ManualMetadata)
        assert record.title
        assert isinstance(record.category_scores, dict)

    # Verify mutating returned objects does not modify SAMPLE_MANUAL_RECORDS
    records[0].title = "Modified Title"
    assert SAMPLE_MANUAL_RECORDS[0].title != "Modified Title"


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
