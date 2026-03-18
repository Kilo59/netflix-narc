"""Client implementation for the Common Sense Media (CSM) API."""

from enum import StrEnum
from pathlib import Path

import hishel
import httpx
from hishel.httpx import SyncCacheClient

from netflix_narc.rating_api import NormalizedMetadata, RatingProvider
from netflix_narc.settings import Settings

HTTP_TOO_MANY_REQUESTS = 429


class CSMRatingCategory(StrEnum):
    """Specific categories evaluated by Common Sense Media."""

    EDUCATIONAL_VALUE = "Educational Value"
    POSITIVE_MESSAGES = "Positive Messages"
    POSITIVE_ROLE_MODELS = "Positive Role Models"
    VIOLENCE = "Violence & Scariness"
    SEXY_STUFF = "Sexy Stuff"
    LANGUAGE = "Language"
    DRINKING_DRUGS = "Drinking, Drugs & Smoking"


class CSMClient(RatingProvider):
    """Client for interacting with the Common Sense Media API with rate-limit caching."""

    BASE_URL = "https://api.commonsensemedia.org/v1"
    provider_name = "csm"

    def __init__(self, settings: Settings, cache_dir: Path | None = None) -> None:
        """Initialize the client.

        Args:
            settings: Application settings, must contain `csm_api_key`.
            cache_dir: Directory to store the hishel HTTP cache. Defaults to `.csm_cache`.
        """
        if not settings.csm_api_key:
            msg = "CSM API Key must be configured to use the CSMClient."
            raise ValueError(msg)

        self.settings = settings
        self._cache_dir = cache_dir or Path(".csm_cache")

        # We use hishel's SyncCacheClient and SyncSqliteStorage.
        self._storage = hishel.SyncSqliteStorage(database_path=str(self._cache_dir))

        self.client = SyncCacheClient(
            storage=self._storage,
            headers={"x-api-key": self.settings.csm_api_key},
            http2=True,
            timeout=10.0,
        )

    def search_title(self, title: str) -> NormalizedMetadata | None:
        """Search for a title in the CSM API and return normalized metadata.

        This method is rate-limited to 5 requests per minute by the API.
        The `hishel` CacheClient ensures we don't make requests for titles we've already seen.
        """
        # Note: This is a mocked implementation outline since we don't have the exact API schema.
        # In a real scenario, this would format the query params per the CSM API docs.
        try:
            response = self.client.get(f"{self.BASE_URL}/reviews", params={"query": title})

            if response.status_code == HTTP_TOO_MANY_REQUESTS:
                msg = "CSM API Rate Limit Exceeded (5 req/min). Please try again later."
                raise RuntimeError(msg)

            response.raise_for_status()

            response.json()
            # For this MVP, we return a mock object if we get a 200 OK.
            # Real implementation would parse `data` into `CSMMetadata`.

            # Normalize CSM metadata to NormalizedMetadata
            # CSM age rating matches content rating (conceptually)
            # CSM quality rating is 1-5, so we normalize to 0-10 (double it)
            return NormalizedMetadata(
                title=title,
                content_rating=str(8),  # Mocked
                user_rating=8.0,  # 4/5 * 2 = 8/10
                provider_name=self.provider_name,
                category_scores={
                    CSMRatingCategory.VIOLENCE.value: 1,
                },
            )

        except httpx.HTTPError:
            # Handle standard HTTP errors
            return None

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self.client.close()
