"""Application-wide settings and configuration schemas."""

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    active_rating_provider: str = "omdb"
    csm_api_key: str = ""
    omdb_api_key: str = ""
    tmdb_api_key: str = ""
    max_age_rating: int = 12
    min_quality_rating: int = 3

    weights: CategoryWeights = CategoryWeights()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
    )
