# The Interrogation Suite TUI Wireframes

Here is the structural layout for how the Textual components will be arranged for the new screens.

## 1. The Lineup Screen

This screen is presented when the user clicks "Start The Lineup" from the main menu. It focuses entirely on a single title to reduce decision fatigue.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ Netflix Narc - The Lineup                                 [Suspect 1 of 50] │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                                                                             │
│                                                                             │
│               ┌────────────────────┐                                        │
│               │                    │                                        │
│               │                    │                                        │
│               │    [TITLE IMAGE]   │   Breaking Bad                         │
│               │      (Poster)      │   Date Watched: 2024-03-12             │
│               │                    │   API Flags: [None]                    │
│               │                    │                                        │
│               │                    │                                        │
│               └────────────────────┘                                        │
│                                                                             │
│                                                                             │
│          ╭────────────────╮  ╭────────────────╮  ╭────────────────╮         │
│          │ [I] Interrogate│  │   [X] Ignore   │  │  [S] Skip      │         │
│          ╰────────────────╯  ╰────────────────╯  ╰────────────────╯         │
│                                                                             │
│                                                                             │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ [Q]uit   [ctrl+s] Search Provider   [?] Help                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Interaction Flow:**
- Pressing `I` or Enter on **Interrogate** pushes the `The Interrogation Room Screen`.
- Pressing `X` on **Ignore** marks the title as ignored in the Evidence Locker (SQLite DB), hides it, and immediately slides the next title into view.
- Pressing `S` on **Skip** leaves the DB untouched but pushes the title to the back of the queue, sliding the next one into view.

---

## 2. The Interrogation Room Screen

This screen slides in over The Lineup when "Interrogate" is selected.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ The Interrogation Room                                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Title: [ Breaking Bad                                               ]      │
│                                                                             │
│  Min Age Rating: [ 18 ]        Quality Rating (1-5): [ 5 ]                  │
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
│                                      │    Cancel      │  │  File Evidence │ │
│                                      ╰────────────────╯  ╰────────────────╯ │
├─────────────────────────────────────────────────────────────────────────────┤
│ [ESC] Cancel   [ctrl+s] Open CSM Search in Browser                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Interaction Flow:**
- `ctrl+s` instantly kicks open the desktop browser to help the user find the info.
- Focus cycles through inputs via `Tab`.
- **File Evidence (Save)**: Writes to the Evidence Locker (SQLite backend), pops this screen, and triggers the "auto-advance" back on The Lineup screen.
