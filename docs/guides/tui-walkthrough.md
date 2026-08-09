# TUI Feature Walkthrough

**netflix-narc** provides a full-featured, keyboard-driven Terminal User Interface built with [Textual](https://textual.textualize.io/).

---

## Global Navigation & Keybindings

Navigate between screens using single-key hotkeys:

| Keybinding | Screen / Action | Description |
|------------|-----------------|-------------|
| <kbd>l</kbd> | **Lineup Screen** | Main discovery queue displaying flagged titles and viewing logs. |
| <kbd>i</kbd> | **Interrogation Room** | Manual rating overrides and Evidence Locker database inspector. |
| <kbd>s</kbd> | **Preferences** | Configure severity category weights and target child age limits. |
| <kbd>?</kbd> | **Help Modal** | Display contextual keyboard shortcuts and navigation commands. |
| <kbd>q</kbd> | **Quit** | Exit netflix-narc safely. |

---

## 1. The Lineup Screen (`l`)

The **Lineup Screen** serves as your primary inspection dashboard. It presents your uploaded viewing history alongside evaluated content safety scores.

![Lineup Screen](../assets/images/lineup_screen.svg){: .tui-screenshot }

### Features

- **Severity Indicators**:
  - 🚨 **High Severity**: Exceeds acceptable safety thresholds (e.g. intense violence or explicit content for target age).
  - ⚠️ **Medium Severity**: Borderline content requiring parental caution or discussion.
  - 🟢 **Low / Safe**: Content verified appropriate for your configured age range.
- **Content Category Breakdown**: Displays scores across Violence, Sex/Nudity, Language, Drugs/Alcohol, and Educational Value.
- **Quick Filtering**: Toggle view between all titles, flagged titles only, or unrated items.

---

## 2. The Interrogation Room (`i`)

When external APIs lack rating data for a niche title, or when you disagree with automated ratings, the **Interrogation Room** allows you to input manual ratings and store evidence locally.

![Interrogation Room](../assets/images/interrogation_screen.svg){: .tui-screenshot }

### Features

- **Manual Data Override**: Enter custom age recommendations and category severity scores for any title.
- **Evidence Locker Store**: Saves your custom notes and overrides into a local async SQLite database (`manual_db.py`).
- **Persistent Local Overrides**: Manual entries take precedence over automated API results during future evaluation runs.

---

## 3. Preferences & Live Weight Impact Preview (`s`)

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
