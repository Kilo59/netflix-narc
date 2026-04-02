---
description: Implementation plan and tasks for the Netflix Narc project.
---

# Implementation Plan

When executing tasks on this project, evaluate progress against the following steps:

## 1. Project Setup
- Validate dependencies in `pyproject.toml` (httpx, hishel, textual, pydantic-settings).

## 2. Netflix Data Ingestion (`src/netflix_narc/parser.py`)
- Parse the Netflix `ViewingHistory.csv` file.
- Clean and normalize titles and watch dates per profile. Return as structured `pydantic` or `TypedDict` objects.

## 3. Configuration Module (`src/netflix_narc/settings.py`)
- Define the `pydantic-settings` model for configuration.
- Fields: `csm_api_key`, `max_age_rating`, `min_quality_rating`, and mapping of category weights.

## 4. API Integration (`src/netflix_narc/csm_api.py`)
- Implement `httpx` client wrapped with `hishel` caching.
- Add robust error handling for HTTP 429 Too Many Requests.
- Parse responses to extract specific categories (Educational Value, Violence, etc.).

## 5. Evaluation Engine (`src/netflix_narc/evaluator.py`)
- Write the logic that accepts a normalized, structured CSM payload and the user's `Settings`.
- Return a list of specific reasons a title is flagged, or an empty list if acceptable.

## 6. Textual TUI (`main.py`)
- Implement an **Onboarding Screen**: Prompt for API key and category weights if they are missing from configuration.
- Implement the **Main Layout**:
  - Sidebar for adjusting criteria dynamically.
  - DataTable showing watched history with flagged titles highlighted in red or yellow depending on severity.
