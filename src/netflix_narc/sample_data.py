"""Sample metadata fixtures for testing, demonstrations, and documentation screenshots."""

from __future__ import annotations

from netflix_narc.manual_db import ManualMetadata

SAMPLE_MANUAL_RECORDS: list[ManualMetadata] = [
    ManualMetadata(
        title="Stranger Things",
        content_rating="TV-14",
        user_rating=8.7,
        image_url="https://example.com/st.jpg",
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
        image_url="https://example.com/paw.jpg",
        category_scores={
            "Violence & Scariness": 1,
            "Educational Value": 5,
            "Positive Messages": 5,
            "Positive Role Models": 5,
            "Language": 1,
            "Sexy Stuff": 1,
        },
    ),
    ManualMetadata(
        title="Squid Game",
        content_rating="TV-MA",
        user_rating=8.0,
        image_url="https://example.com/sg.jpg",
        category_scores={
            "Violence & Scariness": 5,
            "Educational Value": 1,
            "Positive Messages": 1,
            "Positive Role Models": 1,
            "Language": 5,
            "Sexy Stuff": 4,
            "Drinking, Drugs & Smoking": 4,
        },
    ),
    ManualMetadata(
        title="The Magic School Bus",
        content_rating="TV-Y",
        user_rating=7.9,
        image_url="https://example.com/msb.jpg",
        category_scores={
            "Educational Value": 5,
            "Positive Messages": 5,
            "Positive Role Models": 4,
            "Violence & Scariness": 1,
            "Language": 1,
            "Sexy Stuff": 1,
            "Drinking, Drugs & Smoking": 1,
        },
    ),
]


def get_sample_manual_records() -> list[ManualMetadata]:
    """Return a fresh list of sample ManualMetadata records."""
    return [record.model_copy(deep=True) for record in SAMPLE_MANUAL_RECORDS]
