"""Factory for instantiating rating providers based on application settings."""

from netflix_narc.csm_api import CSMClient
from netflix_narc.omdb_api import OMDBClient
from netflix_narc.rating_api import RatingProvider
from netflix_narc.settings import Settings


def get_rating_provider(settings: Settings) -> RatingProvider:
    """Instantiate the active rating provider."""
    provider_type = settings.active_rating_provider.lower()

    if provider_type == "csm":
        return CSMClient(settings)
    if provider_type == "omdb":
        return OMDBClient(settings)
    if provider_type == "tmdb":
        msg = "TMDB provider implementation coming soon."
        raise NotImplementedError(msg)
    msg = f"Unknown rating provider: {provider_type}"
    raise ValueError(msg)
