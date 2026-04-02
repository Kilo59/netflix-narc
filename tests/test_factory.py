"""Unit tests for the provider factory."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pathlib

import pytest
from pydantic import SecretStr

from netflix_narc.csm_api import CSMClient
from netflix_narc.factory import get_rating_provider
from netflix_narc.omdb_api import OMDBClient
from netflix_narc.settings import RatingProviderType, Settings


@pytest.mark.parametrize(
    ("provider_type", "expected_class"),
    [
        (RatingProviderType.CSM, CSMClient),
        (RatingProviderType.OMDB, OMDBClient),
    ],
)
def test_get_rating_provider_success(
    tmp_path: pathlib.Path,
    fake_settings: Settings,
    provider_type: RatingProviderType,
    expected_class: type,
) -> None:
    """Assert the factory returns the correct client for supported types."""
    fake_settings.active_rating_provider = provider_type
    # We pass tmp_path to ensure hishel doesn't write to the real .csm_cache/.omdb_cache
    provider = get_rating_provider(fake_settings, cache_dir=tmp_path)
    assert isinstance(provider, expected_class)
    provider.close()


def test_get_rating_provider_raises_not_implemented(fake_settings: Settings) -> None:
    """Assert NotImplementedError for TMDB."""
    fake_settings.active_rating_provider = RatingProviderType.TMDB
    with pytest.raises(NotImplementedError, match=r"TMDB provider implementation coming soon."):
        get_rating_provider(fake_settings)


def test_get_rating_provider_raises_value_error_on_missing_key(fake_settings: Settings) -> None:
    """Assert ValueError when the required API key for the active provider is missing."""
    fake_settings.active_rating_provider = RatingProviderType.CSM
    fake_settings.csm_api_key = SecretStr("")  # Empty key
    with pytest.raises(ValueError, match=r"CSM API Key must be configured"):
        get_rating_provider(fake_settings)


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
