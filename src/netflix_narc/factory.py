"""Factory for instantiating rating providers based on application settings."""

from __future__ import annotations

from typing import TYPE_CHECKING

from netflix_narc.csm_api import CSMClient
from netflix_narc.omdb_api import OMDBClient
from netflix_narc.settings import RatingProviderType, Settings

if TYPE_CHECKING:
    from netflix_narc.rating_api import RatingProvider


def get_rating_provider(settings: Settings) -> RatingProvider:
    """Instantiate the active rating provider."""
    match settings.active_rating_provider:
        case RatingProviderType.CSM:
            return CSMClient(settings)
        case RatingProviderType.OMDB:
            return OMDBClient(settings)
        case RatingProviderType.TMDB:
            msg = "TMDB provider implementation coming soon."
            raise NotImplementedError(msg)
        case _:
            msg = f"Unknown rating provider: {settings.active_rating_provider}"
            raise ValueError(msg)
