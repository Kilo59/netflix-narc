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

Netflix Narc requires `uv` to run.

### Prerequisites
- Python 3.13+
- A Common Sense Media API Key
- Your exported `NetflixViewingHistory.csv`

### Installation & Usage
1. Clone the repository and navigate into the `netflix-narc` directory.
2. Ensure you have your `NetflixViewingHistory.csv` file available in the root.
   *(You can download this from your Netflix Account Settings under Profile & Parental Controls -> Viewing activity -> Download all).*
3. Run the application using `uv`:
```bash
uv run netflix-narc
```

4. The first time you launch, you will be prompted for your Common Sense Media API key. You can also press `s` at any time to update your key or settings.

### ⌨️ Keybindings

- `l`: Load CSV File
- `e`: Evaluate CSM Data
- `s`: Settings & API Key
- `Enter`: Expand/Collapse a show's episodes
- `q`: Quit Application

## 📜 How it Works
1. You provide your Netflix viewing history.
2. The UI groups your watches by Show/Movie.
3. You press `e` to trigger an evaluation sweep.
4. Netflix Narc cross-references the history against Common Sense Media and highlights exactly where things went wrong based on the `Settings` thresholds.

---

*Built with ❤️ (and a healthy dose of parental suspicion) using Python and Textual.*
