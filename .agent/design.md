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
The [evaluator.py](src/netflix_narc/evaluator.py) module consumes only the `NormalizedMetadata`. It computes suitability scores using one of two user-selectable Scoring Modes (codified in ADRs 11–13):
- **Option A (Quality Focus)**: Quality signals (Base Quality, Educational Suitability, Positive Suitability) drive the base score, and Gate signals (Age Suitability, Safety Suitability) apply penalty-only deductions continuously based on their deficit below perfect.
- **Option B (Balanced)**: Unified weighted average of all 5 components, where Gate signals are capped at `GATE_NEUTRAL_CAP = 7.0` before averaging to prevent boring/low-quality titles from scoring too high.
Additionally, the module flags extreme violations (such as high negative category scores or underage content) based on user-defined weights. This clean separation ensures that adding a new API provider never requires changes to the core evaluation or flagging rules.

## Manual Metadata & Completeness Score
For titles that lack external API data, users can manually enter metadata via the Interrogation Room.
- **Evidence Locker**: Uses `aiosqlite` in [manual_db.py](src/netflix_narc/manual_db.py) to persist this manual data.
- **Completeness Score**: A calculated 0-100% score tracking how completely a title's manual metadata has been filled out. This relies on 10 fields (Ratings, Image URL, and CSM categories).
- **Queue Priority**: The TUI queue strictly sorts unreviewed titles by their `Completeness Score` first (ascending) to guarantee that entirely un-scored titles bubble to the top.
- **Native Image Hook**: A zero-dependency OS hook (via `osascript`) in [image_utils.py](src/netflix_narc/image_utils.py) allows grabbing cover images directly from the macOS clipboard, bypassing standard Textual limitations.
