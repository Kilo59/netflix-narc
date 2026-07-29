"""Data models and schemas for storage and synchronization."""

from __future__ import annotations

import datetime as dt
from typing import ClassVar, Final

from pydantic import BaseModel, ConfigDict, Field

CURRENT_SCHEMA_VERSION: Final[int] = 1


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
    updated_at: str = Field(default_factory=lambda: dt.datetime.now(dt.UTC).isoformat())


class SettingsSyncItem(BaseModel):
    """Serializable snapshot of user preferences (excluding local secrets)."""

    model_config: ClassVar[ConfigDict] = {"extra": "ignore"}

    active_rating_provider: str
    scoring_mode: str
    child_age_range: tuple[int, int] | None = None
    max_age_rating: int
    min_quality_rating: int
    category_weights: dict[str, int] = Field(default_factory=dict)
    updated_at: str = Field(default_factory=lambda: dt.datetime.now(dt.UTC).isoformat())


class SyncBundle(BaseModel):
    """Atomic snapshot payload transferred during sync operations."""

    model_config: ClassVar[ConfigDict] = {"extra": "ignore"}

    version: int = CURRENT_SCHEMA_VERSION
    client_id: str
    timestamp: str = Field(default_factory=lambda: dt.datetime.now(dt.UTC).isoformat())
    settings: SettingsSyncItem | None = None
    evidence_locker: list[DossierSyncItem] = Field(default_factory=list)


class SyncManifest(BaseModel):
    """Metadata manifest of remote storage state."""

    model_config: ClassVar[ConfigDict] = {"extra": "ignore"}

    latest_bundle_id: str
    last_updated: str
    client_id: str
    version: int = CURRENT_SCHEMA_VERSION
