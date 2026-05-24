# The Interrogation Suite Requirements

> [!NOTE]
> This document captures the requirements for creating **The Interrogation Suite**. This suite of features enables users to manually input rating and metadata information for titles, acting as a supplement to or replacement for automated API backends.

## 1. Goal & Overview

Create a Terminal User Interface (TUI) for easily and manually ingesting metadata and rating data.
- **Flexibility**: The manually ingested data must be able to supplement existing backend data (e.g., fill in missing categories) or operate completely independently of other automated ratings data.
- **Workflow**: Leverage the user's parsed Netflix viewing history as a queue. The user can iterate through their viewing history and provide data for titles sequentially or on-demand.
- **Gold Standard**: The data model and fields expected for entry should mirror Common Sense Media (CSM), as it represents the highest standard for the application's evaluation logic.

## 2. Core Features & User Workflow

### 2.1 The Lineup (Priority Queue Workflow)
- The UI should display the titles from the Netflix viewing history (`ViewingHistory.csv`) as a priority queue.
- Titles should be weighted and sorted to present the most actionable items first based on the following rules:
  1. **Flagged for Follow-up**: Titles that the user explicitly flagged for manual review or follow-up.
  2. **Low Quality**: Titles that the automated API evaluators have flagged/deemed low quality based on configured thresholds.
  3. **Recency**: Titles that were most recently watched.
- Titles that already have complete data (either via API or previous manual entry) and do not meet the priority rules above should be pushed lower down or visually distinct.

### 2.2 The Lineup Mode (Steam-Inspired Discovery Queue)
To reduce decision fatigue, the application should offer a "Lineup Mode" that presents titles one at a time:
- **Focused View**: The UI focuses entirely on the single highest-priority title, surfacing its name, any existing API metadata, and a **Title Image** representing the show/movie.
- **Clear Actions**: For the presented title, the user can:
  - **Interrogate**: Open the form to manually enter data.
  - **Ignore**: Mark the title to be permanently hidden from the queue (e.g., for trailers or irrelevant history).
  - **Skip for Now**: Push the title to the back of the queue.
- **Progression**: Display a clear progress indicator (e.g., "Suspect 1 of 50 in your Lineup").
- **Auto-Advance**: Saving data, ignoring, or skipping immediately slides the next title into view.

### 2.3 The Interrogation Room (Data Entry Interface)
When the user chooses to interrogate a title, the UI should present a form for the following fields:
- **Title**: String (pre-filled from viewing history, editable)
- **Age Rating**: Integer (minimum recommended age)
- **Quality Rating**: 1-5 stars
- **Category Scores** (Rated 0 to 5, mirroring CSM):
  - Educational Value
  - Positive Messages
  - Positive Role Models
  - Violence & Scariness
  - Sexy Stuff
  - Language
  - Drinking, Drugs & Smoking
- **Follow-up Flag**: A checkbox or toggle to explicitly flag the title for future follow-up.

### 2.4 Kickstarting Data Gathering
- **Search Provider Shortcut**: A built-in command (e.g., a hotkey like `ctrl+s` or `s` or a UI button) that kicks off a search for the currently selected title at the provider's site.
  - *Implementation*: Use Python's built-in `webbrowser.open()` to launch the user's default desktop browser to a search query (e.g., `https://www.commonsensemedia.org/search/[Title]`).

## 3. Data Integration & Persistence

### 3.1 The Evidence Locker (Storage & Tooling)
- **Database**: Manually entered data will be persisted using a local **SQLite** database.
- **Export/Import Utilities**: The application must provide CLI utilities to easily export the SQLite data into JSON or CSV formats, and import it back into SQLite.

### 3.2 Evaluation & Merging Strategy
- When evaluating a title, the system should attempt to merge the manually entered data with the automated API data.
- **Global Configuration**: The merging behavior (e.g., attempt to merge vs. treat manual as absolute source of truth) must be globally configurable so the user can easily toggle the precedence.
