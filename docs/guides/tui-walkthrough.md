# TUI Feature Walkthrough

**netflix-narc** provides a full-featured, keyboard-driven Terminal User Interface built with [Textual](https://textual.textualize.io/).

---

## Keyboard Shortcuts & Keybindings Reference

### Global Hotkeys

| Keybinding | Screen / Action | Description |
|------------|-----------------|-------------|
| <kbd>l</kbd> | **Lineup Screen** | Open the card-based review queue for sequential title triage. |
| <kbd>i</kbd> | **Interrogation Room** | Edit manual rating overrides and Evidence Locker dossier for the selected title. |
| <kbd>Space</kbd> | **Flag for Follow-up** | Toggle flag for future follow-up on highlighted row or active screen. |
| <kbd>s</kbd> | **Preferences Screen** | Open full preferences panel (weights, scoring mode, provider, BYOS sync). |
| <kbd>a</kbd> | **Advanced Options** | Progressive disclosure modal for power-user actions. |
| <kbd>h</kbd> or <kbd>?</kbd> | **Help Screen** | Display contextual help, philosophy, and keyboard reference. |
| <kbd>c</kbd> | **Load History File** | Reload or open a new Netflix viewing history CSV file. |
| <kbd>e</kbd> | **Evaluate Titles** | Trigger rating metadata fetches for unrated titles via active provider API. |
| <kbd>q</kbd>, <kbd>F10</kbd>, <kbd>Ctrl+C</kbd> | **Quit App** | Safely exit **netflix-narc**. |

### Screen & Context Hotkeys

| Context | Keybinding | Action | Description |
|---------|------------|--------|-------------|
| **Main Table** | <kbd>Enter</kbd> | **Expand / Collapse** | Toggle 5 sub-suitability breakdown bars for highlighted row. |
| **Main Table** | <kbd>Space</kbd> | **Flag for Follow-up** | Toggle flag for future follow-up on highlighted row. |
| **Lineup Queue** | <kbd>i</kbd> | **Interrogate** | Open Interrogation Room for current card title. |
| **Lineup Queue** | <kbd>Space</kbd> | **Flag for Follow-up** | Toggle flag for future follow-up on current card title. |
| **Lineup Queue** | <kbd>x</kbd> | **Ignore Title** | Mark current title as ignored and advance to next item. |
| **Lineup Queue** | <kbd>s</kbd> | **Skip Title** | Skip current title without modifying its status. |
| **Interrogation** | <kbd>Space</kbd> | **Flag for Follow-up** | Toggle 'Flag for future follow-up' checkbox (when form input non-focused). |
| **Interrogation** | <kbd>F2</kbd> | **Web Search** | Open Common Sense Media search for title in default browser. |
| **Modals / Screens** | <kbd>Esc</kbd> | **Close / Back** | Dismiss current screen or modal dialog without saving changes. |

---

## 1. Main Inspection Table (Home Screen)

Upon launching **netflix-narc** after setup, your uploaded Netflix viewing history is presented in the **Main Inspection Table**.

![Main Inspection Table](../assets/images/datatable_expanded.svg){: .tui-screenshot }

### Features

- **Row Expansion (<kbd>Enter</kbd>)**: Press <kbd>Enter</kbd> or click any row to expand/collapse detailed sub-suitability breakdown bars.
- **Color-Coded Suitability Bars**: Displays overall suitability scores from `0.0/10` to `10.0/10` (🟢 Green $\ge 7.5$, 🟡 Yellow $\ge 5.0$, 🔴 Red $< 5.0$).
- **View Count & Watch Dates**: Displays total view count and first/last watch dates extracted from your Netflix CSV.
### Sub-Suitability Breakdown Bars

When a row is expanded in the main inspection table or inspected in the Interrogation Room, **netflix-narc** displays 5 sub-suitability bars:

| Sub-Bar | Description |
|---------|-------------|
| **Base Quality** | User/critic quality score out of 10.0. |
| **Age Suitability** | Compatibility with your child's age range. |
| **Educational Suitability** | Educational value score scaled by your custom weight. |
| **Positive Content** | Combined score for positive messages and positive role models. |
| **Content Safety** | Combined safety score penalizing violence, sexual content, language, and substance use. |

---

## 2. The Lineup Screen (`l`)

Press <kbd>l</kbd> to enter **The Lineup Screen**—a sequential, card-based review queue designed for fast, focused title triage.

![Lineup Screen](../assets/images/lineup_screen.svg){: .tui-screenshot }

### Features & Actions

- **Sequential Card View**: Displays titles one at a time with title metadata, view count, and watch history dates.
- **Dossier Completeness Progress Bar**: Shows current Evidence Locker completeness (e.g., `[████████░░] 80%`).
- **Triage Actions**:
  - <kbd>i</kbd> **Interrogate**: Open the Interrogation Room to input manual category ratings and notes.
  - <kbd>x</kbd> **Ignore**: Mark the title as ignored so it drops out of active review queues.
  - <kbd>s</kbd> **Skip**: Skip to the next title in the review queue.

---

## 3. The Interrogation Room (`i`)

When external APIs lack rating data for a niche title, or when you disagree with automated ratings, the **Interrogation Room** provides a manual data entry and evaluation workbench.

![Interrogation Room](../assets/images/interrogation_screen.svg){: .tui-screenshot }

### Features & Capabilities

- **Real-Time Suitability Dashboard**: Recalculates overall suitability scores and color-coded sub-bars in real-time as you type or adjust scores.
- **5 Sub-Suitability Score Bars**: Visual indicators for Base Quality, Age Suitability, Educational Suitability, Positive Content, and Content Safety.
- **Category Severity Scores**: Input 0–5 rating scores for:
  - *Violence & Scariness*, *Language*, *Sexy Stuff*, *Drinking, Drugs & Smoking*, *Educational Value*, *Positive Messages*, *Positive Role Models*.
- **Quality Rating (1.0–5.0 stars)**: Input star ratings which are clamped and mapped to normalized 0–10 scores.
- **Cover Image Attachment**:
  - **Paste Image from Clipboard**: On macOS, click **Paste Cover Image** to attach an image from your clipboard directly into the dossier.
  - **URL Download**: Enter any HTTP(S) image URL to auto-download and store cover art locally.
- **Web Search Shortcut (<kbd>F2</kbd>)**: Opens Common Sense Media search for the active title in your web browser.
- **Flag for Follow-up**: Checkbox to mark titles requiring further parental discussion.
- **Async Evidence Locker Storage**: Saves your custom notes, scores, and image references into a local SQLite database (`manual_db.sqlite`). Manual entries override or supplement API metadata.

---

## 4. Preferences & Live Weight Impact Preview (`s`)

Press <kbd>s</kbd> to open the **Preferences Screen** to tune your evaluation algorithm.

![Preferences Screen](../assets/images/preferences_screen.svg){: .tui-screenshot }

### Scoring Modes

**netflix-narc** supports two evaluation algorithms depending on your family's filtering philosophy:

- **Option A: Quality Focus (`quality_focus`)**:
  - Base Quality and Positive Content drive the initial suitability score.
  - Gate factors (**Age Suitability** and **Content Safety**) act strictly as penalty deductions.
  - *Best for*: Parents who want high-quality family shows to shine, but want inappropriate or mature content penalized heavily regardless of how high its critic score is.
- **Option B: Balanced (`balanced`)** *(Default)*:
  - All 5 sub-suitability components contribute to a weighted average score.
  - Neutral safety factors are capped at `7.0/10` to maintain realistic score balance.
  - *Best for*: A holistic view where high educational value or positive messages can offset mild content concerns.

### Category Sensitivity Weights

Customizable 1–5 scale sliders let you tune how aggressively specific concerns lower suitability:

- **Overall Signals**: Base Quality weight, Age Suitability weight.
- **Content Categories**: Educational Value, Positive Messages, Positive Role Models, Violence & Scariness, Sexual Content, Language, Drinking/Drugs/Smoking.

### Live Weight Impact Preview

During Onboarding and inside Preferences, **netflix-narc** renders a side-by-side **Weight Impact Preview** panel:

- **Before / After Suitability Bars**: Displays instant visual comparison bars showing how your weight changes adjust suitability scores across sample titles in your Evidence Locker.
- **Delta Indicator**: Shows exact numeric score shifts (e.g., `+1.2` or `-0.8`).
- **📌 Pin a Title Selector**: Allows you to pin a specific title to watch its suitability score react in real-time as you tweak individual sliders.

---

## 5. The Help Screen (`h` / `?`)

Press <kbd>h</kbd> or <kbd>?</kbd> at any time to open the **Help Screen**.

![Help Screen](../assets/images/help_screen.svg){: .tui-screenshot }

### Content & References

- **App Philosophy & Guidance**: Explains how **netflix-narc** balances parental guidance and content evaluation.
- **Scoring System Overview**: Quick reference for suitability thresholds and color bars.
- **Keyboard Shortcut Reference**: Comprehensive table of global and screen-specific hotkeys.

---

## 6. Advanced Options Modal (`a`)

Press <kbd>a</kbd> to open the **Advanced Options** modal for progressive disclosure of power-user actions.

![Advanced Options Modal](../assets/images/advanced_screen.svg){: .tui-screenshot }

### Actions & Configuration

- **Load History File (<kbd>c</kbd>)**: Prompts to reload or switch Netflix viewing history CSV files.
- **Evaluate Titles via API (<kbd>e</kbd>)**: Manually trigger rating metadata fetches from the configured rating provider.
- **Max Records to Load**: Limit the number of recent viewing history items processed (default: 200).
- **Min Quality Rating**: Filter threshold for minimum CSM quality stars (1-5).
- **Max Age Rating**: Upper age threshold for content evaluation.
- **Merge Evidence Locker Data Switch**: Enable/disable merging manual database dossier overrides into API results.
