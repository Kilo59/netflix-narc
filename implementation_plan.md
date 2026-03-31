# Completion Plan: Rating API Abstraction

The objective is to finish the ongoing architectural shift to a plugin-based rating provider system. While the core interfaces are in place, several components remain mocked or unimplemented.

## Accomplished So Far
- [x] **`src/netflix_narc/rating_api.py`**: Defined `NormalizedMetadata` and the `RatingProvider` protocol.
- [x] **`src/netflix_narc/factory.py`**: Implemented the provider factory.
- [x] **`src/netflix_narc/evaluator.py`**: Refactored to consume `NormalizedMetadata`.
- [x] **`src/netflix_narc/main.py`**: Initial integration with the factory and provider interface.

## Remaining Tasks

### 1. Concrete CSM Implementation
Modify [csm_api.py](src/netflix_narc/csm_api.py) to replace the mock logic with real API interaction.
- Implement proper parsing of the JSON response.
- Map CSM-specific ratings (1-5) to the normalized 0-10 scale.
- Handle rate-limiting (5 req/min) gracefully beyond simple RuntimeError.

### 2. Add OMDb Support
Create a new module to verify the multi-provider abstraction.
- **[NEW] `src/netflix_narc/omdb_api.py`**:
  - Implement `OMDBClient(RatingProvider)`.
  - Handle OMDb-specific fields (e.g., `imdbRating`, `Rated`).
- **Update `get_rating_provider`**: Register the new client in the factory.

### 3. UI and Configuration Enhancements
Update [main.py](src/netflix_narc/main.py) to support switching providers.
- **`SetupScreen`**: Add a selection for the active provider.
- **Persistence**: Ensure `ACTIVE_RATING_PROVIDER` is saved to `.env` along with provider-specific keys.
- **Dynamic Loading**: Refresh the `rating_provider` when settings change without requiring an app restart.

### 4. Automated Testing
Fulfill the original verification plan:
- [ ] Unit tests for `NormalizedMetadata` validation.
- [ ] Mocked integration tests for `CSMClient` and `OMDBClient`.
- [ ] Factory tests ensuring correct instantiation.

## Open Questions
- Do we want to support **fallback providers** (e.g., if CSM fails, try OMDb)?
- Should we normalize content ratings (PG, R, etc.) to a numeric scale for easier evaluation, or keep them as strings?

## Verification Plan
### Automated Tests
- `pytest tests/test_rating_api.py`
- `pytest tests/test_providers.py`

### Manual Verification
- Launch the TUI, switch to OMDb via settings, and verify that evaluations still work using OMDb data.
