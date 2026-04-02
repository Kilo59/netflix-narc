"""Client implementation for the Common Sense Media (CSM) API."""

from __future__ import annotations

import pathlib
from enum import StrEnum
from typing import TYPE_CHECKING, Any, override

import hishel
import httpx
from hishel.httpx import SyncCacheClient

from netflix_narc.rating_api import NormalizedMetadata, RatingProvider

if TYPE_CHECKING:
    from netflix_narc.settings import Settings

HTTP_TOO_MANY_REQUESTS = 429

# CSM quality ratings are 1-5 stars; we normalise to 0-10 by doubling.
_CSM_RATING_SCALE_FACTOR = 2


class CSMRatingCategory(StrEnum):
    """Specific categories evaluated by Common Sense Media."""

    EDUCATIONAL_VALUE = "Educational Value"
    POSITIVE_MESSAGES = "Positive Messages"
    POSITIVE_ROLE_MODELS = "Positive Role Models"
    VIOLENCE = "Violence & Scariness"
    SEXY_STUFF = "Sexy Stuff"
    LANGUAGE = "Language"
    DRINKING_DRUGS = "Drinking, Drugs & Smoking"


# Map snake_case keys returned by the CSM API to canonical display names.
_CSM_CATEGORY_KEY_MAP: dict[str, str] = {
    "educational_value": CSMRatingCategory.EDUCATIONAL_VALUE,
    "positive_messages": CSMRatingCategory.POSITIVE_MESSAGES,
    "positive_role_models": CSMRatingCategory.POSITIVE_ROLE_MODELS,
    "violence": CSMRatingCategory.VIOLENCE,
    "sexy_stuff": CSMRatingCategory.SEXY_STUFF,
    "language": CSMRatingCategory.LANGUAGE,
    "drinking_drugs": CSMRatingCategory.DRINKING_DRUGS,
}


def _parse_csm_response(title: str, data: list[dict[str, Any]]) -> NormalizedMetadata | None:
    """Parse the CSM API ``data`` array into a ``NormalizedMetadata`` instance.

    Returns ``None`` when the data list is empty (title not found).

    Expected shape of each entry in ``data``::

        {
            "id": "123",
            "title": "The Matrix",
            "age": 14,  # minimum recommended age (int)
            "rating": 4,  # 1-5 star quality rating (int)
            "categories": {  # granular scores, snake_case keys
                "violence": 3,
                "language": 2,
                "sexy_stuff": 1,
            },
        }

    Args:
        title: The original query title (used as fallback when API omits it).
        data: The ``data`` array from the CSM JSON response body.

    Returns:
        A ``NormalizedMetadata`` instance, or ``None`` if ``data`` is empty.
    """
    if not data:
        return None

    entry = data[0]

    # Age rating: CSM returns an integer minimum age.
    age_val = entry.get("age")
    content_rating = str(age_val) if isinstance(age_val, int) else None

    # Quality rating: CSM 1-5 stars -> normalised 0-10 scale by doubling.
    raw_rating = entry.get("rating")
    user_rating = (
        float(raw_rating * _CSM_RATING_SCALE_FACTOR)
        if isinstance(raw_rating, (int, float))
        else None
    )

    # Category scores: map snake_case API keys → canonical display-name keys.
    raw_categories: dict[str, Any] = entry.get("categories") or {}
    category_scores: dict[str, int | float] = {}
    for api_key, score in raw_categories.items():
        canonical = _CSM_CATEGORY_KEY_MAP.get(api_key)
        if canonical and isinstance(score, (int, float)):
            category_scores[canonical] = score

    return NormalizedMetadata(
        title=str(entry.get("title", title)),
        content_rating=content_rating,
        user_rating=user_rating,
        provider_name="csm",
        category_scores=category_scores,
    )


class CSMClient(RatingProvider):
    """Client for interacting with the Common Sense Media API with rate-limit caching."""

    BASE_URL = "https://api.commonsensemedia.org/v1"
    provider_name = "csm"

    def __init__(
        self,
        settings: Settings,
        cache_dir: pathlib.Path | None = None,
        **kwargs: Any,  # noqa: ANN401, ARG002
    ) -> None:
        """Initialize the client.

        Args:
            settings: Configuration settings for the client.
            cache_dir: Optional directory for HTTP caching.
            **kwargs: Additional keyword arguments.
        """
        if not settings.csm_api_key.get_secret_value():
            msg = "CSM API Key must be configured to use the CSMClient."
            raise ValueError(msg)

        self.settings = settings
        self._cache_dir = cache_dir or pathlib.Path(".csm_cache")

        # We use hishel's SyncCacheClient and SyncSqliteStorage.
        # Pass a file path (not a directory) for the sqlite DB.
        cache_path = str(self._cache_dir / "cache.sqlite")
        self._storage = hishel.SyncSqliteStorage(database_path=cache_path)

        self.client = SyncCacheClient(
            storage=self._storage,
            headers={"x-api-key": self.settings.csm_api_key.get_secret_value()},
            http2=True,
            timeout=10.0,
        )

    @override
    def search_title(self, title: str, *, cache_only: bool = False) -> NormalizedMetadata | None:
        """Search for a title in the CSM API and return normalized metadata."""
        headers = {}
        if cache_only:
            headers["Cache-Control"] = "only-if-cached"

        try:
            response = self.client.get(
                f"{self.BASE_URL}/reviews", params={"query": title}, headers=headers
            )

            if response.status_code == HTTP_TOO_MANY_REQUESTS:
                msg = "CSM API Rate Limit Exceeded (5 req/min). Please try again later."
                raise RuntimeError(msg)

            response.raise_for_status()

            body = response.json()
            data: list[dict[str, Any]] = body.get("data", [])
            return _parse_csm_response(title, data)

        except httpx.HTTPError:
            # Handle standard HTTP errors
            return None

    @override
    def close(self) -> None:
        """Close the underlying HTTP client."""
        self.client.close()
