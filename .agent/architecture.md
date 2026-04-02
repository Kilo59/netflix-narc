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
- **Configuration & Settings**: `pydantic-settings`
- **Data Models**: `pydantic` (for data payloads, avoid untyped dicts)
- **Dependency Management**: `uv`

## Project Structure (Target)
- `src/netflix_narc/parser.py`: Parses the standard `ViewingHistory.csv` using the built-in `csv` module.
- `src/netflix_narc/csm_api.py`: Fetches CSM data via HTTP. MUST implement `hishel` caching to avoid hitting the 5 request/minute API limit.
- `src/netflix_narc/settings.py`: Uses `pydantic-settings` to load the CSM `x-api-key`, age rating thresholds, and category weighting configurations.
- `src/netflix_narc/evaluator.py`: Compares CSM metadata against the user's weighted criteria (e.g., "Language: High Priority", "Violence: Rejection Threshold"). returns flagged reasons.
- `main.py`: The Textual app entrypoint. Orchestrates the onboarding screen (for gathering the API key and initial user weights) and the main data table view.

## AI Agent Rules for this Project
1. **Never mock the cache logic**: When working on `csm_api.py`, ensure `hishel` is always correctly intercepting and returning cached HTTP responses to avoid rate limits.
2. **Onboarding First**: If `Settings` cannot find the `x-api-key`, the TUI MUST intercept execution and present an interactive onboarding view to gather it and initial criteria weights.
3. **Dependency restraint**: Unless heavily justified, do not pull in heavy parsing libraries like `pandas`; rely on standard library modules (e.g., `csv`, `json`) combined with `pydantic`.
4. **Strict Typing**: Use Python 3.13 features. Pass data around using typed `pydantic` models or `TypedDict` where appropriate. Highly discourage passing around raw, untyped `dict` objects.
