# Welcome to netflix-narc 🕵️‍♂️🎬

**netflix-narc** is a modern, privacy-first Terminal User Interface (TUI) and command-line utility built for parents, guardians, and caregivers. It helps you monitor, analyze, and flag potentially inappropriate content in your family's Netflix viewing history based on customizable, age-appropriate safety thresholds.

!!! note "Privacy First"
    All viewing history evaluation is performed locally on your device. Your Netflix credentials are never requested or stored, and your viewing logs never leave your computer.

![netflix-narc Lineup Screen TUI Preview](assets/images/lineup_screen.svg){: .tui-screenshot }

---

## Key Features

- 📥 **Automated CSV Ingestion**: Effortlessly import your official Netflix `ViewingHistory.csv` export.
- 🌐 **Multi-Provider Rating Intelligence**: Fetches rich content metadata and granular age recommendations from **Common Sense Media (CSM)**, **OMDb**, and **The Movie Database (TMDB)**.
- ⚖️ **Customizable Severity Weights**: Fine-tune rating sensitivity across content categories including Violence, Sex/Nudity, Language, Drug/Alcohol Use, and Educational Value.
- ⚡ **Offline Caching & Evidence Locker**: Powered by `hishel` caching to minimize API requests and an async SQLite database to store manual overrides and local ratings.
- 💻 **Interactive Terminal UI**: Seamlessly review flagged titles, inspect content breakdowns, and adjust preferences using a sleek keyboard-driven Textual interface.

---

## Where to Start?

Whether you are running `netflix-narc` for the first time or customizing your safety rules, explore the sections below:

<div class="grid cards" markdown>

-   :material-download: **[Installation](getting-started/installation.md)**

    Download standalone pre-built binaries for macOS, Linux, or Windows, or install via `uv`/`pip`.

-   :material-file-document-outline: **[Exporting Netflix History](getting-started/exporting-netflix-csv.md)**

    Step-by-step visual guide on exporting your official `ViewingHistory.csv` from Netflix Account Settings.

-   :material-wizard-hat: **[Onboarding & Setup](guides/onboarding-and-setup.md)**

    Walk through the first-run configuration wizard and optional API key setups for OMDb, TMDB, and CSM.

-   :material-monitor-dashboard: **[TUI Feature Walkthrough](guides/tui-walkthrough.md)**

    Explore the Lineup Screen, Interrogation Room, and Live Weight Impact Preview controls.

</div>

---

## Quick Command Line Preview

```bash
# Launch the interactive TUI interface
netflix-narc

# Pass a Netflix Viewing History CSV directly
netflix-narc --csv ~/Downloads/NetflixViewingHistory.csv
```
