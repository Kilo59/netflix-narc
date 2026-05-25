# TUI Wireframes & Mockups

Here is the structural layout for how the Textual components will be arranged for the new screens.

## 1. Discovery Queue Screen

This screen is presented when the user clicks "Start Queue Mode" from the main menu. It focuses entirely on a single title to reduce decision fatigue.

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

## 2. Manual Entry Screen

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
