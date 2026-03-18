from netflix_narc.csm_api import CSMClient
from netflix_narc.rating_api import RatingProvider
from netflix_narc.settings import Settings


def get_rating_provider(settings: Settings) -> RatingProvider:
    """Factory function to instantiate the active rating provider."""
    provider_type = settings.active_rating_provider.lower()

    if provider_type == "csm":
        return CSMClient(settings)
    # Future providers (omdb, tmdb, tms) will be added here
    if provider_type == "omdb":
        raise NotImplementedError("OMDb provider implementation coming soon.")
    if provider_type == "tmdb":
        raise NotImplementedError("TMDB provider implementation coming soon.")
    raise ValueError(f"Unknown rating provider: {provider_type}")
