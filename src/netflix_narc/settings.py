"""Application-wide settings and configuration schemas."""

from __future__ import annotations

from enum import StrEnum
from typing import ClassVar

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class RatingProviderType(StrEnum):
    """Available rating providers for the application."""

    CSM = "csm"
    OMDB = "omdb"
    TMDB = "tmdb"


class CategoryWeights(BaseSettings):
    """Configuration for how much weight to apply to specific CSM categories.

    A higher weight means the category is strictly discouraged.
    Categories scoring poorly on CSM multiplied by these weights will flag the title.
    """

    educational_value: int = 1
    positive_messages: int = 1
    positive_role_models: int = 1
    violence: int = 3
    sexy_stuff: int = 3
    language: int = 2
    drinking_drugs: int = 3


class Settings(BaseSettings):
    """Core application configuration."""

    model_config: ClassVar[SettingsConfigDict] = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "env_nested_delimiter": "__",
    }

    active_rating_provider: RatingProviderType = RatingProviderType.OMDB
    csm_api_key: SecretStr = SecretStr("")
    omdb_api_key: SecretStr = SecretStr("")
    tmdb_api_key: SecretStr = SecretStr("")
    max_age_rating: int = 12
    min_quality_rating: int = 3
    max_records: int = 200

    weights: CategoryWeights = CategoryWeights()
