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
- `src/netflix_narc/settings.py`: Uses `pydantic-settings` to load the CSM `x-api-key`, age rating thresholds, and category weighting configurations.
- `src/netflix_narc/evaluator.py`: Compares CSM metadata against the user's weighted criteria (e.g., "Language: High Priority", "Violence: Rejection Threshold"). returns flagged reasons.
- `src/netflix_narc/manual_db.py`: The "Evidence Locker", using `aiosqlite` to store manually entered metadata for titles that external APIs can't score.
- `src/netflix_narc/lineup.py`: The "Lineup Screen" TUI component for iterating through the queue of flagged or un-scored titles.
- `src/netflix_narc/interrogation_room.py`: The "Interrogation Room Screen" for manual entry of CSM criteria for titles missing API data.
- `src/netflix_narc/main.py`: The Textual app entrypoint (`NetflixNarcApp`). Orchestrates onboarding, the data table, and pushing the manual entry screens.

## AI Agent Rules for this Project
1. **Never mock the cache logic**: When working on `csm_api.py`, ensure `hishel` is always correctly intercepting and returning cached HTTP responses to avoid rate limits.
2. **Onboarding First**: If `Settings` cannot find the `x-api-key`, the TUI MUST intercept execution and present an interactive onboarding view to gather it and initial criteria weights.
3. **Dependency restraint**: Unless heavily justified, do not pull in heavy parsing libraries like `pandas`; rely on standard library modules (e.g., `csv`, `json`) combined with `pydantic`.
4. **Strict Typing**: Use Python 3.13 features. Pass data around using typed `pydantic` models or `TypedDict` where appropriate. Highly discourage passing around raw, untyped `dict` objects.
5. **Async DB over Threads**: For local storage, use `aiosqlite` so that database writes (Evidence Locker) don't block the Textual TUI event loop. Avoid `threading.Thread` workers in favor of Textual's `@work` or `asyncio.create_task`.
