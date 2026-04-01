"""Tests for the OMDb and Common Sense Media API clients.

Uses respx to mock all HTTP calls — no network requests are made.
Always passes cache_dir=tmp_path so hishel writes are sandboxed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest
import respx
from pydantic import SecretStr

from netflix_narc.csm_api import CSMClient
from netflix_narc.omdb_api import OMDBClient
from netflix_narc.settings import Settings

if TYPE_CHECKING:
    import pathlib

# ---------------------------------------------------------------------------
# OMDb Client Tests
# ---------------------------------------------------------------------------


def test_omdb_search_happy_path(
    tmp_path: pathlib.Path,
    fake_settings: Settings,
    omdb_response_payload: dict[str, str],
) -> None:
    """OMDBClient.search_title returns NormalizedMetadata on a successful response."""
    with respx.mock:
        respx.get("http://www.omdbapi.com/").mock(
            return_value=httpx.Response(200, json=omdb_response_payload)
        )
        client = OMDBClient(settings=fake_settings, cache_dir=tmp_path)
        result = client.search_title("The Matrix")
        client.close()

    assert result is not None
    assert result.title == "The Matrix"
    assert result.content_rating == "R"
    assert result.user_rating == pytest.approx(8.7)
    assert result.provider_name == "omdb"
    assert result.category_scores == {}


def test_omdb_search_returns_none_on_false_response(
    tmp_path: pathlib.Path,
    fake_settings: Settings,
) -> None:
    """OMDBClient.search_title returns None when the API reports Response=False."""
    payload = {"Response": "False", "Error": "Movie not found!"}
    with respx.mock:
        respx.get("http://www.omdbapi.com/").mock(return_value=httpx.Response(200, json=payload))
        client = OMDBClient(settings=fake_settings, cache_dir=tmp_path)
        result = client.search_title("Nonexistent Movie")
        client.close()

    assert result is None


def test_omdb_search_handles_na_rating(
    tmp_path: pathlib.Path,
    fake_settings: Settings,
    omdb_response_payload: dict[str, str],
) -> None:
    """OMDBClient.search_title normalizes imdbRating='N/A' to user_rating=None."""
    payload = {**omdb_response_payload, "imdbRating": "N/A", "Rated": "N/A"}
    with respx.mock:
        respx.get("http://www.omdbapi.com/").mock(return_value=httpx.Response(200, json=payload))
        client = OMDBClient(settings=fake_settings, cache_dir=tmp_path)
        result = client.search_title("Unknown Rating Movie")
        client.close()

    assert result is not None
    assert result.user_rating is None
    assert result.content_rating is None


def test_omdb_search_returns_none_on_http_error(
    tmp_path: pathlib.Path,
    fake_settings: Settings,
) -> None:
    """OMDBClient.search_title returns None when the server returns an HTTP error."""
    with respx.mock:
        respx.get("http://www.omdbapi.com/").mock(return_value=httpx.Response(500))
        client = OMDBClient(settings=fake_settings, cache_dir=tmp_path)
        result = client.search_title("Error Movie")
        client.close()

    assert result is None


# ---------------------------------------------------------------------------
# CSM Client Tests
# ---------------------------------------------------------------------------


def test_csm_client_raises_on_empty_key(tmp_path: pathlib.Path) -> None:
    """CSMClient raises ValueError when instantiated without an API key."""
    settings = Settings(csm_api_key=SecretStr(""), _env_file=None)  # type: ignore[call-arg]
    with pytest.raises(ValueError, match="CSM API Key must be configured"):
        CSMClient(settings=settings, cache_dir=tmp_path)


def test_csm_search_raises_on_rate_limit(
    tmp_path: pathlib.Path,
    fake_settings: Settings,
) -> None:
    """CSMClient.search_title raises RuntimeError on HTTP 429 (rate limit exceeded)."""
    with respx.mock:
        respx.get("https://api.commonsensemedia.org/v1/reviews").mock(
            return_value=httpx.Response(429)
        )
        client = CSMClient(settings=fake_settings, cache_dir=tmp_path)
        with pytest.raises(RuntimeError, match="Rate Limit"):
            client.search_title("Any Title")
        client.close()


def test_csm_search_happy_path(
    tmp_path: pathlib.Path,
    fake_settings: Settings,
) -> None:
    """CSMClient.search_title returns NormalizedMetadata on a successful response."""
    payload: dict[str, object] = {"data": []}  # MVP client returns mock data on any 200
    with respx.mock:
        respx.get("https://api.commonsensemedia.org/v1/reviews").mock(
            return_value=httpx.Response(200, json=payload)
        )
        client = CSMClient(settings=fake_settings, cache_dir=tmp_path)
        result = client.search_title("The Matrix")
        client.close()

    assert result is not None
    assert result.provider_name == "csm"
    assert result.content_rating is not None


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
