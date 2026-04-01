# Completion Plan: Rating API (OMDb Priority)

The objective is to pivot our implementation to focus on an API with generous rate limits for initial "dogfooding" and development. While CSM is the ultimate high-quality target, its 5 req/min limit makes rapid testing difficult. We will prioritize **OMDb** (1,000 req/day) as our primary working provider and ensure **hishel caching** is implemented from the start to minimize redundant calls.

## User Review Required
> [!IMPORTANT]
> - **Caching First**: Every provider must use `hishel` with a local SQLite backend to ensure we don't waste API quota during development.
> - **Pivoting to OMDb**: We'll gain the ability to evaluate entire watch histories quickly.
> - OMDb's `category_scores` (Violence, Language, etc.) are less granular than CSM's. We will need to map OMDb's `Genre` and `Plot` where possible, or rely primarily on `Rated` and `imdbRating` in the interim.


## Accomplished So Far
- [x] **`src/netflix_narc/rating_api.py`**: Defined `NormalizedMetadata` and `RatingProvider`.
- [x] **`src/netflix_narc/factory.py`**: Implemented the provider factory.
- [x] **`src/netflix_narc/evaluator.py`**: Refactored to consume `NormalizedMetadata`.
- [x] **`src/netflix_narc/main.py`**: Initial integration with the factory and provider interface.
- [x] **Documentation**: Captured architectural design in [.agent/design.md](.agent/design.md).

## Proposed Changes

### 1. Implement OMDb Provider
Create the first fully-functional API provider using OMDb.
- **[NEW] `src/netflix_narc/omdb_api.py`**:
  - Implement `OMDBClient(RatingProvider)`.
  - Fetch from `http://www.omdbapi.com/` using the `t` (Title) parameter.
  - Map `Rated` (e.g., "PG-13") -> `content_rating`.
  - Map `imdbRating` (e.g., "8.8") -> `user_rating`.
  - Ensure `hishel` caching is integrated to keep the 1,000/day limit manageable.
- **Update `get_rating_provider`**: Register `OMDBClient` in [factory.py](src/netflix_narc/factory.py).

### 2. UI and Configuration Enhancements
Update [main.py](src/netflix_narc/main.py) to make OMDb the default and configurable.
- **`SetupScreen`**: Add a selection for "Active Provider" (CSM, OMDb).
- **Persistence**: Save `ACTIVE_RATING_PROVIDER` and `OMDB_API_KEY` to `.env`.
- **Default Switch**: Change default `active_rating_provider` in [settings.py](src/netflix_narc/settings.py) to `omdb`.

### 3. Concrete CSM Implementation (Downgraded Priority)
Complete the [csm_api.py](src/netflix_narc/csm_api.py) implementation but treat it as secondary until the API key/limit issues are addressed for the dev team.

### 4. Automated Testing
- [ ] Unit tests for `NormalizedMetadata` validation.
- [ ] Mocked integration tests for `OMDBClient` (using `respx`).
- [ ] Factory tests ensuring correct instantiation based on `Settings`.

## Open Questions
- Should we add a **bulk lookup** mode to OMDb (using IDs) or stick to title-based search for the MVP?

## Verification Plan
### Automated Tests
- `pytest tests/test_rating_api.py`
- `pytest tests/test_providers.py`

### Manual Verification
1. Launch the TUI.
2. Select "OMDb" in settings and enter a valid key.
3. Verify that history rows populate with "Passed" or specific flags using OMDb data.
