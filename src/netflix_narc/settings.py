"""Application-wide settings and configuration schemas."""

from __future__ import annotations

import pathlib
import re
from enum import StrEnum
from typing import ClassVar, Final

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_CSV_FILENAME: Final[pathlib.Path] = pathlib.Path("NetflixViewingHistory.csv")


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
    child_age_range: tuple[int, int] | None = None
    max_age_rating: int = 12
    min_quality_rating: int = 3
    max_records: int = 200
    merge_manual_data: bool = True

    weights: CategoryWeights = CategoryWeights()

    @field_validator("child_age_range", mode="before")
    @classmethod
    def parse_child_age_range(cls, v: object) -> tuple[int, int] | None:
        """Parse various flexible input formats into a clean tuple[int, int]."""
        if v is None:
            return None
        if isinstance(v, tuple):
            expected_len = 2
            if len(v) == expected_len and isinstance(v[0], int) and isinstance(v[1], int):
                return v
            try:
                return (int(v[0]), int(v[1]))
            except (ValueError, TypeError, IndexError):
                pass
        if isinstance(v, list):
            try:
                return (int(v[0]), int(v[1]))
            except (ValueError, TypeError, IndexError):
                pass
        if isinstance(v, str):
            return parse_str_age_range(v)
        err_msg = f"Invalid age range format: {v}"
        raise ValueError(err_msg)


def parse_str_age_range(v_str: str) -> tuple[int, int] | None:
    """Helper to parse a string age range."""
    val = v_str.strip().lower()
    if not val:
        return None
    parts_str = re.findall(r"\d+", val)
    parts = [int(p) for p in parts_str]
    if not parts:
        err_msg = f"Could not parse age range from string: {v_str}"
        raise ValueError(err_msg)
    if len(parts) == 1:
        return (parts[0], parts[0])
    return (parts[0], parts[1])
