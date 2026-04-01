"""Client implementation for the OMDb API."""

from pathlib import Path
from typing import override

import hishel
import httpx
from hishel.httpx import SyncCacheClient

from netflix_narc.rating_api import NormalizedMetadata, RatingProvider
from netflix_narc.settings import Settings


class OMDBClient(RatingProvider):
    """Client for interacting with the OMDb API with hishel caching."""

    BASE_URL = "http://www.omdbapi.com/"
    provider_name = "omdb"

    def __init__(self, settings: Settings, cache_dir: Path | None = None) -> None:
        """Initialize the client with settings and caching.

        Args:
            settings: Application settings, must contain `omdb_api_key`.
            cache_dir: Directory to store the hishel HTTP cache. Defaults to `.omdb_cache`.
        """
        if not settings.omdb_api_key.get_secret_value():
            msg = "OMDb API Key must be configured to use the OMDBClient."
            raise ValueError(msg)

        self.settings = settings
        self._cache_dir = cache_dir or Path(".omdb_cache")

        # Persistent storage for hishel
        cache_path = str(self._cache_dir / "cache.sqlite")
        self._storage = hishel.SyncSqliteStorage(database_path=cache_path)

        self.client = SyncCacheClient(
            storage=self._storage,
            http2=True,
            timeout=10.0,
        )

    @override
    def search_title(self, title: str, *, cache_only: bool = False) -> NormalizedMetadata | None:
        """Search for a title and return normalized metadata."""
        params = {
            "t": title,
            "apikey": self.settings.omdb_api_key.get_secret_value(),
        }

        headers = {}
        if cache_only:
            headers["Cache-Control"] = "only-if-cached"

        try:
            response = self.client.get(self.BASE_URL, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()

            if data.get("Response") == "False":
                return None

            # Handle N/A in imdbRating
            raw_rating = data.get("imdbRating")
            user_rating = float(raw_rating) if raw_rating and raw_rating != "N/A" else None

            # OMDb 'Rated' field is the content rating (PG-13, R, etc.)
            content_rating = data.get("Rated")
            if content_rating == "N/A":
                content_rating = None

            return NormalizedMetadata(
                title=data.get("Title", title),
                content_rating=content_rating,
                user_rating=user_rating,
                provider_name=self.provider_name,
                category_scores={},  # OMDb doesn't provide granular scores
            )

        except (httpx.HTTPError, ValueError):
            return None

    @override
    def close(self) -> None:
        """Close the underlying HTTP client."""
        self.client.close()
