# Netflix Narc 🕵️‍♂️🍿

**Your automated, terminal-based snitch.**

Netflix Narc is a fast, beautiful Terminal UI built to ingest your family's Netflix viewing history, cross-reference it with the **Common Sense Media API**, and gently narc on anyone watching something they shouldn't.

Whether it's too violent, contains sketchy language, or is just completely devoid of educational value, you decide the criteria, and Netflix Narc tells you who's been watching it.

## ✨ Features

- **🍿 Netflix Integration**: Easily ingest your profile's `ViewingHistory.csv`.
- **🧠 Common Sense Intel**: Automatically fetches age ratings, quality scores, and granular category breakdowns (Violence, Language, Educational Value, etc.) from Common Sense Media.
- **⚖️ Weighted Justice**: Customize how strictly you want to judge different content categories.
- **🖥️ Beautiful TUI**: A gorgeous, reactive terminal interface powered by Textual.
- **⚡️ Fast & Polite**: Intelligent caching ensures we don't spam the API or get rate-limited.

## 🚀 Getting Started

### Prerequisites
- Python 3.13+
- [uv](https://github.com/astral-sh/uv) (for lightning-fast dependency management)
- A Common Sense Media API Key

### Installation

Clone the repo and install dependencies:
```bash
git clone https://github.com/yourusername/netflix-narc.git
cd netflix-narc
uv sync
```

### Running the App

```bash
uv run textual run main.py
```

*Note: On your first run, the built-in onboarding flow will guide you through entering your API key and setting up your baseline judgement criteria!*

## 📜 How it Works
1. Go to your [Netflix Account Settings](https://www.netflix.com/settings/viewing-history) and select **Download all** to get your `ViewingHistory.csv`.
2. Boot up Netflix Narc.
3. Watch the app cross-reference your history against your personal Common Sense thresholds and highlight exactly where things went wrong.

---

*Built with ❤️ (and a healthy dose of parental suspicion) using Python and Textual.*
