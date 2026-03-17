# Goal Description
The objective is to make the application flexible enough to use multiple APIS to evaluate a user's viewing history. Currently, the app is hardcoded to use [CSMClient](src/netflix_narc/csm_api.py#40-106) (Common Sense Media) and its specialized [CSMMetadata](src/netflix_narc/csm_api.py#23-38). We will introduce a new abstraction/interface that standardizes the metadata across different providers (OMDb, TMDB, TMS, CSM) and allows easy swapping or combining of these APIs.

## Proposed Changes

We will introduce a new module `src/netflix_narc/rating_api.py` (or modify the existing API structure) containing the abstract interfaces and normalized data models.

### `src/netflix_narc/rating_api.py` (New Module)
This file will define the core abstractions.

- **[NEW] `NormalizedMetadata` (Pydantic Model)**:
  A standardized model representing the common denominator across all APIs.
  ```python
  class NormalizedMetadata(BaseModel):
      title: str
      content_rating: str | None = Field(default=None, description="Standard content rating (e.g., PG-13, TV-MA).")
      user_rating: float | None = Field(default=None, description="Normalized 0.0 - 10.0 user rating scale.")
      provider_name: str = Field(description="Name of the API provider (e.g., 'omdb', 'tmdb').")
      category_scores: dict[str, int | float] = Field(
          default_factory=dict,
          description="Scores for specific advanced criteria (e.g., 'Violence & Scariness', 'Language', 'Educational Value'). Typically 0-5."
      )
      # Provider-specific raw data can optionally be retained here, or specific subclasses can extend it.
  ```

- **[NEW] `RatingProvider` (Protocol / ABC)**:
  An interface that all specific API clients must implement.
  ```python
  from typing import Protocol

  class RatingProvider(Protocol):
      provider_name: str

      def search_title(self, title: str) -> NormalizedMetadata | None:
          """Search for a title and return its normalized metadata."""
          ...

      def close(self) -> None:
          """Cleanup resources."""
          ...
  ```

### [src/netflix_narc/csm_api.py](src/netflix_narc/csm_api.py)
- Modify [CSMClient](src/netflix_narc/csm_api.py#40-106) to implement the new `RatingProvider` Protocol.
- It will return `NormalizedMetadata`, possibly by mapping [CSMMetadata](src/netflix_narc/csm_api.py#23-38)'s `age_rating` to a `content_rating` representation, and `quality_rating` to the 0-10 `user_rating` scale.

### [src/netflix_narc/settings.py](src/netflix_narc/settings.py)
- Add settings to configure which provider to use.
  ```python
  class Settings(BaseSettings):
      ...
      active_rating_provider: str = Field(default="csm", description="Which API to use: csm, omdb, tmdb, etc.")
      omdb_api_key: str | None = None
      tmdb_api_key: str | None = None
  ```

### Provider Factory (e.g., `src/netflix_narc/factory.py`)
- We will need a factory function or dependency injection configuration to instantiate the correct `RatingProvider` based on the `active_rating_provider` setting.

## Verification Plan
1. **Automated Tests**:
   - Write unit tests for the abstract `NormalizedMetadata` model.
   - Write tests ensuring [CSMClient](src/netflix_narc/csm_api.py#40-106) correctly implements `RatingProvider` and normalizes its specific data to `NormalizedMetadata`.
2. **Manual Verification**:
   - N/A for this phase, as the goal is only to capture the architectural design.
