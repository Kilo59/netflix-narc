---
description: Detailed design of the Rating API abstraction layer.
---

# Rating API Design

The application is built around a pluggable rating provider system. This allows the evaluator logic to remain agnostic of the specific API source (CSM, OMDb, TMDB, etc.).

## Core Abstractions

### 1. `NormalizedMetadata` (Pydantic Model)
Located in [rating_api.py](src/netflix_narc/rating_api.py).
This model standardizes the disparate response formats from various APIs into a common internal representation.

```python
class NormalizedMetadata(BaseModel):
    title: str
    content_rating: str | None  # Standard rating (e.g., PG-13, TV-MA)
    user_rating: float | None    # Normalized 0.0 - 10.0 scale
    provider_name: str           # The source API (e.g., 'csm', 'omdb')
    category_scores: dict[str, int | float] # Specific criteria scores (0-5)
```

### 2. `RatingProvider` (Protocol)
Located in [rating_api.py](src/netflix_narc/rating_api.py).
A standard interface that all API clients must implement.

- `search_title(title: str) -> NormalizedMetadata | None`: The primary method for fetching and normalizing data.
- `close() -> None`: Resource cleanup.

## Factory Pattern
A centralized factory in [factory.py](src/netflix_narc/factory.py) orchestrates the instantiation of providers based on the `active_rating_provider` setting.

```python
def get_rating_provider(settings: Settings) -> RatingProvider:
    # Resolves 'csm' -> CSMClient, 'omdb' -> OMDBClient, etc.
```

## Provider Implementation Strategy

### Common Sense Media (CSM)
- **Status**: Backend implemented, integration mocked.
- **Normalizations**:
  - `Age Rating` (e.g., 8+) -> `content_rating`.
  - `Quality Rating` (1-5) -> `user_rating` (multiplied by 2 for 0-10 scale).
- **Caching**: Mandatory `hishel` integration to respect the 5 req/min rate limit.

### OMDb (Planned)
- **Status**: Design only.
- **Normalizations**:
  - `Rated` -> `content_rating`.
  - `imdbRating` (0-10) -> `user_rating`.

## Evaluation Logic
The [evaluator.py](src/netflix_narc/evaluator.py) module consumes only the `NormalizedMetadata`. It applies user-defined weights (from `Settings`) to the `category_scores` to generate flags. This separation ensures that adding a new API provider never requires changes to the core evaluation rules.
