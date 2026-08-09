"""Sample metadata fixtures for testing, demonstrations, and documentation screenshots."""

from __future__ import annotations

from netflix_narc.manual_db import ManualMetadata

SAMPLE_MANUAL_RECORDS: list[ManualMetadata] = [
    ManualMetadata(
        title="Stranger Things",
        content_rating="TV-14",
        user_rating=8.7,
        image_url="http://example.com/st.jpg",
        category_scores={
            "Violence & Scariness": 4,
            "Educational Value": 2,
            "Positive Messages": 3,
            "Positive Role Models": 3,
            "Language": 3,
            "Sexy Stuff": 2,
        },
    ),
    ManualMetadata(
        title="PAW Patrol: The Movie",
        content_rating="G",
        user_rating=6.1,
        image_url="http://example.com/paw.jpg",
        category_scores={
            "Violence & Scariness": 1,
            "Educational Value": 5,
            "Positive Messages": 5,
            "Positive Role Models": 5,
            "Language": 1,
            "Sexy Stuff": 1,
        },
    ),
]


def get_sample_manual_records() -> list[ManualMetadata]:
    """Return a fresh list of sample ManualMetadata records."""
    return [record.model_copy(deep=True) for record in SAMPLE_MANUAL_RECORDS]
