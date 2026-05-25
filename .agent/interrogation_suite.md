# The Interrogation Suite Requirements & Design

> [!NOTE]
> This document captures the requirements and design mockups for **The Interrogation Suite**. This suite of features enables users to manually input rating and metadata information for titles, acting as a supplement to or replacement for automated API backends.

## 1. Goal & Overview

Create a Terminal User Interface (TUI) for easily and manually ingesting metadata and rating data.
- **Flexibility**: The manually ingested data must be able to supplement existing backend data (e.g., fill in missing categories) or operate completely independently of other automated ratings data.
- **Workflow**: Leverage the user's parsed Netflix viewing history as a queue. The user can iterate through their viewing history and provide data for titles sequentially or on-demand.
- **Gold Standard**: The data model and fields expected for entry should mirror Common Sense Media (CSM), as it represents the highest standard for the application's evaluation logic.

## 2. Core Features & User Workflow

### 2.1 The Lineup (Priority Queue Workflow)
- The UI should display the titles from the Netflix viewing history (`ViewingHistory.csv`) as a priority queue.
- Titles should be weighted and sorted to present the most actionable items first based on the following rules:
  1. **Completeness Score (Primary Weight)**: Titles strictly sorted by ascending completion status (0-100%). Completely empty records appear first.
  2. **Flagged for Follow-up**: Titles that the user explicitly flagged for manual review or follow-up.
  3. **Low Quality**: Titles that the automated API evaluators have flagged/deemed low quality based on configured thresholds.
  4. **Recency**: Titles that were most recently watched.
- Titles that already have complete data (either via API or previous manual entry) and do not meet the priority rules above should be pushed lower down or visually distinct.

### 2.2 The Lineup Mode (Steam-Inspired Discovery Queue)
To reduce decision fatigue, the application should offer a "Lineup Mode" that presents titles one at a time:
- **Focused View**: The UI focuses entirely on the single highest-priority title, surfacing its name, any existing API metadata, and a **Title Image** representing the show/movie.
- **Clear Actions**: For the presented title, the user can:
  - **Interrogate**: Open the form to manually enter data.
  - **Ignore**: Mark the title to be permanently hidden from the queue (e.g., for trailers or irrelevant history).
  - **Skip for Now**: Push the title to the back of the queue.
- **Progression**: Display a clear progress indicator (e.g., "Suspect 1 of 50 in your Lineup") along with a **Dossier Completeness** progress bar (e.g. `[████░░░░░░] 40%`).
- **Auto-Advance**: Saving data, ignoring, or skipping immediately slides the next title into view.

### 2.3 The Interrogation Room (Data Entry Interface)
When the user chooses to interrogate a title, the UI should present a form for the following fields:
- **Title**: String (pre-filled from viewing history, editable)
- **Age Rating**: Integer (minimum recommended age)
- **Quality Rating**: 1-5 stars
- **Cover Image**: An HTTP URL or local path. Supports a native macOS `pbpaste` OS hook allowing the user to click a "Paste" button to directly rip binary images from their clipboard and automatically download/save them locally, bypassing Textual's text-only clipboard limitations.
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
- **Search Provider Shortcut**: A built-in command (e.g., a hotkey like `ctrl+s` or `F2` or a UI button) that kicks off a search for the currently selected title at the provider's site.
  - *Implementation*: Use Python's built-in `webbrowser.open()` to launch the user's default desktop browser to a search query (e.g., `https://www.commonsensemedia.org/search/[Title]`).

## 3. Data Integration & Persistence

### 3.1 The Evidence Locker (Storage & Tooling)
- **Database**: Manually entered data will be persisted using an asynchronous local **SQLite** database (`aiosqlite`) to avoid blocking the TUI event loop.
- **Local Images**: Images obtained through the Interrogation Room are normalized and saved into the `.evidence_images/` directory.

---

## 4. TUI Wireframes & Mockups

### 4.1 Discovery Queue Screen

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ Netflix Narc - Discovery Queue                              [ Title 1 of 50]│
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                                                                             │
│                                                                             │
│               ┌────────────────────┐                                        │
│               │                    │                                        │
│               │                    │                                        │
│               │    [TITLE IMAGE]   │   Title: Breaking Bad                  │
│               │      (Poster)      │   Views: 42                            │
│               │                    │   First Watched: 2023-01-15            │
│               │                    │   Last Watched: 2024-03-12             │
│               │                    │                                        │
│               │                    │   Dossier Completeness: [████░░░░░░] 40%
│               └────────────────────┘                                        │
│                                                                             │
│                                                                             │
│          ╭────────────────╮  ╭────────────────╮  ╭────────────────╮         │
│          │ [I] Ingest Data│  │   [X] Ignore   │  │  [S] Skip      │         │
│          ╰────────────────╯  ╰────────────────╯  ╰────────────────╯         │
│                                                                             │
│                                                                             │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ [Q]uit   [ctrl+s] Search Provider   [?] Help                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Interaction Flow:**
- Queue is strictly ordered first by **Completeness Score (ascending)** so titles missing data appear first, then by view count (descending).
- Pressing `I` or Enter on **Ingest Data** pushes the `ManualEntryScreen`.
- Pressing `X` on **Ignore** marks the title as ignored in the SQLite DB, hides it, and immediately slides the next title into view.
- Pressing `S` on **Skip** leaves the DB untouched but pushes the title to the back of the queue, sliding the next one into view.

---

### 4.2 Manual Entry Screen

This screen slides in over the Discovery Queue when "Ingest Data" is selected.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ Manual Data Entry                                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Title: [ Breaking Bad                                               ]      │
│                                                                             │
│  Min Age Rating: [ 18 ]        Quality Rating (1-5): [ 5 ]                  │
│  Cover Image:    [ https://...                  ]  [ Paste ]                │
│                                                                             │
│  CSM Category Scores (0-5)                                                  │
│  ─────────────────────────                                                  │
│  Educational Value:         [ 1 ]                                           │
│  Positive Messages:         [ 1 ]                                           │
│  Positive Role Models:      [ 1 ]                                           │
│  Violence & Scariness:      [ 4 ]                                           │
│  Sexy Stuff:                [ 2 ]                                           │
│  Language:                  [ 5 ]                                           │
│  Drinking, Drugs & Smoking: [ 5 ]                                           │
│                                                                             │
│                                                                             │
│  [ ] Flag for future follow-up                                              │
│                                                                             │
│                                                                             │
│                                      ╭────────────────╮  ╭────────────────╮ │
│                                      │    Cancel      │  │    Save        │ │
│                                      ╰────────────────╯  ╰────────────────╯ │
├─────────────────────────────────────────────────────────────────────────────┤
│ [ESC] Cancel   [F2] Open Web Search                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Interaction Flow:**
- `ctrl+s` instantly kicks open the desktop browser to help the user find the info.
- Focus cycles through inputs via `Tab`.
- **Save**: Writes to the `manual_db.py` SQLite backend, pops this screen, and triggers the "auto-advance" back on the Discovery Queue screen.
