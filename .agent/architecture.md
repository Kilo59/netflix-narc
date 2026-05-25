---
description: System architecture, context, and core principles for the Netflix Narc project.
---

# Netflix Narc Context & Architecture

## Core Purpose
A CLI/TUI application that ingests Netflix viewing history, fetches metadata and age ratings from the Common Sense Media (CSM) API, and flags inappropriate content based on customizable, weighted criteria.

## Tech Stack
- **Python >= 3.13**
- **TUI Framework**: `textual`
- **HTTP Client**: `httpx`
- **HTTP Caching**: `hishel` (CRITICAL for CSM API rate limits)
- **Database**: `aiosqlite` (Async SQLite persistence for manual metadata)
- **Configuration & Settings**: `pydantic-settings`
- **Data Models**: `pydantic` (for data payloads, avoid untyped dicts)
- **Dependency Management**: `uv`

## Project Structure (Target)
- `src/netflix_narc/parser.py`: Parses the standard `ViewingHistory.csv` using the built-in `csv` module.
- `src/netflix_narc/csm_api.py`: Fetches CSM data via HTTP. MUST implement `hishel` caching to avoid hitting the 5 request/minute API limit.
- `src/netflix_narc/settings.py`: Uses `pydantic-settings` to load API keys, age rating thresholds, and category weighting configurations. `get_config_dir()` returns the XDG config dir (`~/.config/netflix-narc/`).
- `src/netflix_narc/evaluator.py`: Compares CSM metadata against the user's weighted criteria (e.g., "Language: High Priority", "Violence: Rejection Threshold"). Returns flagged reasons.
- `src/netflix_narc/persistence.py`: Writes settings (including all `WEIGHTS__*` fields) to `~/.config/netflix-narc/.env` atomically.
- `src/netflix_narc/manual_db.py`: The "Evidence Locker", using `aiosqlite` to store manually entered metadata for titles that external APIs can't score.
- `src/netflix_narc/onboarding.py`: **[PLANNED]** Multi-step first-run wizard (`OnboardingScreen`). Steps: Welcome → Age → Weights → API Keys → Summary. See `.agent/onboarding_overhaul.md`.
- `src/netflix_narc/preferences.py`: **[PLANNED]** Always-accessible settings panel (`PreferencesScreen`), bound to `s`. Replaces `SetupScreen`.
- `src/netflix_narc/lineup.py`: The "Lineup Screen" TUI component for iterating through the queue of flagged or un-scored titles.
- `src/netflix_narc/interrogation_room.py`: The "Interrogation Room Screen" for manual entry of CSM criteria for titles missing API data.
- `src/netflix_narc/image_utils.py`: Native macOS utilities (osascript/pbpaste equivalents) to bypass TUI limitations for binary clipboard access and image downloading.
- `src/netflix_narc/main.py`: The Textual app entrypoint (`NetflixNarcApp`). Orchestrates onboarding, the data table, and pushing the manual entry screens.

## AI Agent Rules for this Project
1. **Never mock the cache logic**: When working on `csm_api.py`, ensure `hishel` is always correctly intercepting and returning cached HTTP responses to avoid rate limits.
2. **Onboarding First**: `needs_onboarding = settings.child_age_range is None`. When true, push `OnboardingScreen`. API keys are *never* a blocker — they are optional and collected on a skippable step. See `.agent/onboarding_overhaul.md`.
3. **Config Dir for persistence**: All settings writes go to `get_config_dir() / ".env"` (`~/.config/netflix-narc/.env`). Never write to a CWD-relative `.env`.
4. **Dependency restraint**: Unless heavily justified, do not pull in heavy parsing libraries like `pandas`; rely on standard library modules (e.g., `csv`, `json`) combined with `pydantic`.
5. **Strict Typing**: Use Python 3.13 features. Pass data around using typed `pydantic` models or `TypedDict` where appropriate. Highly discourage passing around raw, untyped `dict` objects.
6. **Async DB over Threads**: For local storage, use `aiosqlite` so that database writes (Evidence Locker) don't block the Textual TUI event loop. Avoid `threading.Thread` workers in favor of Textual's `@work` or `asyncio.create_task`.
