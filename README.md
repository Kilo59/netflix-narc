# Netflix Narc 🕵️‍♂️🍿

![Netflix Narc Hero Art](./assets/hero.png)

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

Netflix Narc is currently in active development.

### Prerequisites
- Python 3.13+
- A Common Sense Media API Key

## 📜 How it Works
1. You provide your Netflix viewing history.
2. You define your personal thresholds (e.g., maximum age rating, tolerance for "Language" or "Violence").
3. Netflix Narc cross-references the history against Common Sense Media and highlights exactly where things went wrong.

---

*Built with ❤️ (and a healthy dose of parental suspicion) using Python and Textual.*
