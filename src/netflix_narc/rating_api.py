"""Standardized interfaces for title rating API providers."""

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field


class NormalizedMetadata(BaseModel):
    """Standardized metadata model representing the common denominator across all APIs."""

    title: str
    content_rating: str | None = Field(
        default=None, description="Standard content rating (e.g., PG-13, TV-MA)."
    )
    user_rating: float | None = Field(
        default=None, description="Normalized 0.0 - 10.0 user rating scale."
    )
    provider_name: str = Field(description="Name of the API provider (e.g., 'csm', 'omdb').")
    category_scores: dict[str, int | float] = Field(
        default_factory=dict,
        description="Scores for specific advanced criteria"
        " (e.g., 'Violence & Scariness', 'Language'). Typically 0-5.",
    )


@runtime_checkable
class RatingProvider(Protocol):
    """Interface that all specific API clients must implement."""

    provider_name: str

    def search_title(self, title: str, *, cache_only: bool = False) -> NormalizedMetadata | None:
        """Search for a title and return its normalized metadata."""
        ...

    def close(self) -> None:
        """Cleanup resources."""
        ...
