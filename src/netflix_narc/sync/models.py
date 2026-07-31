"""Data models and schemas for storage and synchronization."""

from __future__ import annotations

import datetime as dt
import logging
from typing import ClassVar, Final

from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)

CURRENT_SCHEMA_VERSION: Final[int] = 1


def ensure_utc(v: object) -> dt.datetime:
    """Validate and convert flexible inputs into a timezone-aware UTC datetime."""
    res: dt.datetime | None = None
    if isinstance(v, dt.datetime):
        res = v
    elif isinstance(v, (int, float)):
        res = dt.datetime.fromtimestamp(v, tz=dt.UTC)
    elif isinstance(v, str) and v.strip():
        try:
            res = dt.datetime.fromisoformat(v.strip())
        except (ValueError, TypeError):
            logger.warning("Failed to parse ISO datetime from '%s', falling back to epoch UTC", v)
            return dt.datetime.fromtimestamp(0, tz=dt.UTC)
    else:
        return dt.datetime.fromtimestamp(0, tz=dt.UTC)

    if res.tzinfo is None:
        return res.replace(tzinfo=dt.UTC)
    return res.astimezone(dt.UTC)


class DossierSyncItem(BaseModel):
    """Serializable record for an Evidence Locker title dossier."""

    model_config: ClassVar[ConfigDict] = {"extra": "ignore"}

    title: str
    content_rating: str | None = None
    user_rating: float | None = None
    image_url: str | None = None
    flagged_for_followup: bool = False
    ignored: bool = False
    category_scores: dict[str, float] = Field(default_factory=dict)
    updated_at: dt.datetime | str = Field(default_factory=lambda: dt.datetime.now(dt.UTC))

    @field_validator("updated_at", mode="before")
    @classmethod
    def _validate_updated_at(cls, v: object) -> dt.datetime:
        return ensure_utc(v)


class SettingsSyncItem(BaseModel):
    """Serializable snapshot of user preferences (excluding local secrets)."""

    model_config: ClassVar[ConfigDict] = {"extra": "ignore"}

    active_rating_provider: str
    scoring_mode: str
    child_age_range: tuple[int, int] | None = None
    max_age_rating: int
    min_quality_rating: int
    category_weights: dict[str, int] = Field(default_factory=dict)
    updated_at: dt.datetime | str = Field(default_factory=lambda: dt.datetime.now(dt.UTC))

    @field_validator("updated_at", mode="before")
    @classmethod
    def _validate_updated_at(cls, v: object) -> dt.datetime:
        return ensure_utc(v)


class SyncBundle(BaseModel):
    """Atomic snapshot payload transferred during sync operations."""

    model_config: ClassVar[ConfigDict] = {"extra": "ignore"}

    version: int = CURRENT_SCHEMA_VERSION
    client_id: str
    timestamp: dt.datetime | str = Field(default_factory=lambda: dt.datetime.now(dt.UTC))
    settings: SettingsSyncItem | None = None
    evidence_locker: list[DossierSyncItem] = Field(default_factory=list)

    @field_validator("timestamp", mode="before")
    @classmethod
    def _validate_timestamp(cls, v: object) -> dt.datetime:
        return ensure_utc(v)


class SyncManifest(BaseModel):
    """Metadata manifest of remote storage state."""

    model_config: ClassVar[ConfigDict] = {"extra": "ignore"}

    latest_bundle_id: str
    last_updated: dt.datetime | str = Field(default_factory=lambda: dt.datetime.now(dt.UTC))
    client_id: str
    version: int = CURRENT_SCHEMA_VERSION

    @field_validator("last_updated", mode="before")
    @classmethod
    def _validate_last_updated(cls, v: object) -> dt.datetime:
        return ensure_utc(v)
