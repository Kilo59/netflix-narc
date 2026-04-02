"""Shared pytest fixtures for netflix-narc tests."""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from netflix_narc.settings import Settings


@pytest.fixture()
def fake_settings() -> Settings:
    """Return a Settings instance with fake API keys and no real .env file.

    The `_env_file=None` kwarg prevents pydantic-settings from loading the
    real .env file, ensuring tests are hermetic.

    In tests that instantiate API clients, pass `cache_dir=tmp_path` directly
    to the client constructor to sandbox hishel's sqlite writes.
    """
    return Settings(
        csm_api_key=SecretStr("fake-csm-key"),
        omdb_api_key=SecretStr("fake-omdb-key"),
        tmdb_api_key=SecretStr("fake-tmdb-key"),
        _env_file=None,  # type: ignore[call-arg]
    )


@pytest.fixture()
def omdb_response_payload() -> dict[str, str]:
    """Return a canonical OMDb API success response payload.

    Matches the real OMDb JSON shape. Use this as a baseline and override
    individual fields in tests that need specific values.
    """
    return {
        "Title": "The Matrix",
        "Year": "1999",
        "Rated": "R",
        "Released": "31 Mar 1999",
        "Genre": "Action, Sci-Fi",
        "imdbRating": "8.7",
        "imdbID": "tt0133093",
        "Type": "movie",
        "Response": "True",
    }


@pytest.fixture()
def csm_response_payload() -> dict[str, object]:
    """Return a canonical CSM API success response payload.

    Matches the expected CSM JSON shape. Use as a baseline in CSM client tests.
    """
    return {
        "data": [
            {
                "id": "123",
                "title": "The Matrix",
                "age": 14,
                "rating": 4,
                "categories": {
                    "violence": 3,
                    "language": 2,
                    "sexy_stuff": 1,
                },
            }
        ]
    }
