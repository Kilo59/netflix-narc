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

### Features

- **Manual Data Override**: Enter custom age recommendations and category severity scores for any title.
- **Evidence Locker Store**: Saves your custom notes and overrides into a local async SQLite database (`manual_db.py`).
- **Persistent Local Overrides**: Manual entries take precedence over automated API results during future evaluation runs.

---

## 3. Preferences & Live Weight Impact Preview (`s`)

Press <kbd>s</kbd> to open the **Preferences Screen** to tune your evaluation algorithm.

### Features

- **Category Sensitivity Sliders**: Adjust weights for individual content concerns (e.g., set Violence weight higher than Language weight).
- **Live Weight Impact Preview**: As you adjust sliders, the preview panel dynamically recalculates how many titles in your viewing history flip between Safe, Warning, and Flagged states.
