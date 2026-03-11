from enum import Enum
from pathlib import Path

import hishel
import httpx
from pydantic import BaseModel, ConfigDict, Field

from netflix_narc.settings import Settings


class CSMRatingCategory(str, Enum):
    """Specific categories evaluated by Common Sense Media."""

    EDUCATIONAL_VALUE = "Educational Value"
    POSITIVE_MESSAGES = "Positive Messages"
    POSITIVE_ROLE_MODELS = "Positive Role Models"
    VIOLENCE = "Violence & Scariness"
    SEXY_STUFF = "Sexy Stuff"
    LANGUAGE = "Language"
    DRINKING_DRUGS = "Drinking, Drugs & Smoking"


class CSMMetadata(BaseModel):
    """Represents the relevant data returned by the CSM API for a particular title."""

    title: str
    age_rating: int | None = Field(
        default=None, description="The recommended minimum age (e.g., 8)."
    )
    quality_rating: int | None = Field(
        default=None, description="The overall quality rating out of 5."
    )
    category_scores: dict[CSMRatingCategory, int] = Field(
        default_factory=dict, description="Scores for specific categories (typically 0-5)."
    )

    model_config = ConfigDict(frozen=True)


class CSMClient:
    """Client for interacting with the Common Sense Media API with rate-limit caching."""

    BASE_URL = "https://api.commonsensemedia.org/v1"

    def __init__(self, settings: Settings, cache_dir: Path | None = None):
        """Initialize the client.

        Args:
            settings: Application settings, must contain `csm_api_key`.
            cache_dir: Directory to store the hishel HTTP cache. Defaults to `.csm_cache`.
        """
        if not settings.csm_api_key:
            raise ValueError("CSM API Key must be configured to use the CSMClient.")

        self.settings = settings
        self._cache_dir = cache_dir or Path(".csm_cache")

        # We use hishel's SyncCacheClient and SyncSqliteStorage.
        self._storage = hishel.SyncSqliteStorage(database_path=str(self._cache_dir))
        
        from hishel.httpx import SyncCacheClient
        
        self.client = SyncCacheClient(
            storage=self._storage,
            headers={"x-api-key": self.settings.csm_api_key},
            http2=True,
            timeout=10.0,
        )

    def search_title(self, title: str) -> CSMMetadata | None:
        """Search for a title in the CSM API and return normalized metadata.

        This method is rate-limited to 5 requests per minute by the API.
        The `hishel` CacheClient ensures we don't make requests for titles we've already seen.
        """
        # Note: This is a mocked implementation outline since we don't have the exact API schema.
        # In a real scenario, this would format the query params per the CSM API docs.
        try:
            response = self.client.get(f"{self.BASE_URL}/reviews", params={"query": title})

            if response.status_code == 429:
                raise RuntimeError(
                    "CSM API Rate Limit Exceeded (5 req/min). Please try again later."
                )

            response.raise_for_status()

            data = response.json()
            # For this MVP, we return a mock object if we get a 200 OK.
            # Real implementation would parse `data` into `CSMMetadata`.
            return CSMMetadata(
                title=title,
                age_rating=8,
                quality_rating=4,
                category_scores={CSMRatingCategory.VIOLENCE: 1},
            )

        except httpx.HTTPError as e:
            # Handle standard HTTP errors
            print(f"Error fetching data for {title}: {e}")
            return None

    def close(self):
        """Close the underlying HTTP client."""
        self.client.close()
