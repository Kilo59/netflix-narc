# Implementation Plan — Zensical Documentation Site Setup & User Guides

Resolves Issue: [#27](https://github.com/Kilo59/netflix-narc/issues/27)
Context Reference: [`ruff-sync#141`](https://github.com/Kilo59/ruff-sync/issues/141)

## Goal

Build a modern, user-friendly, and media-rich documentation site for **netflix-narc** using **Zensical** (the high-performance, Rust-powered successor to Material for MkDocs).

Because `netflix-narc` targets non-technical users (parents, guardians, caregivers monitoring family viewing habits), this documentation site prioritizes visual clarity, step-by-step guidance, annotated screenshots, and terminal UI recordings over dense technical API/CLI reference specs.

---

## Agent Intelligence & Task Difficulty Matrix

To optimize agent resource allocation, tasks are divided into three difficulty tiers based on required intelligence and complexity:

| Tier | Recommended Agent Level | Model Suggestion | Task Nature |
|------|-------------------------|------------------|-------------|
| 🟢 **Tier 1: Low** | Basic / "Dumb" Agent | `flash_lite` / `flash` | Mechanical file creation, exact config snippets (`pyproject.toml`, `tasks.py`, `CONTRIBUTING.md`, `zensical.toml`), directory creation. |
| 🟡 **Tier 2: Medium** | Standard Agent | `flash` / `pro` | Drafting structured user guides (`exporting-netflix-csv.md`, `tui-walkthrough.md`, `troubleshooting-faq.md`), writing GitHub Actions deployment workflow. |
| 🔴 **Tier 3: High** | High Intelligence Agent | `pro` / `high` | Visual asset capture (TUI screenshots & `vhs` recordings), custom Zensical CSS theme matching TUI aesthetics, cross-link validation, end-to-end static site verification. |

---

## Modifiable Agent Task Checklist

> **Instructions for Worker Agents**: Check off tasks `[x]` as you complete them. If a task encounters issues, add a note under the corresponding task checkbox.

### 🟢 Tier 1: Low Difficulty Tasks (Basic / "Dumb" Agents)

- [x] **Task 1.1**: Update `pyproject.toml` to add `docs = ["zensical>=0.1.0"]` under `[dependency-groups]`. Run `uv lock`.
- [x] **Task 1.2**: Create `zensical.toml` in repository root with standard project metadata and theme config.
- [x] **Task 1.3**: Update `tasks.py` to add `docs_serve` and `docs_build` invoke tasks.
- [x] **Task 1.4**: Update `CONTRIBUTING.md` with documentation local preview commands (`uv run inv docs-serve`).
- [x] **Task 1.5**: Create directory structure: `docs/getting-started/`, `docs/guides/`, `docs/assets/images/`, `docs/assets/recordings/`.

### 🟡 Tier 2: Medium Difficulty Tasks (Standard Agents)

- [x] **Task 2.1**: Write `docs/index.md` — Parent-focused introduction, feature highlights, and navigation callouts.
- [x] **Task 2.2**: Write `docs/getting-started/installation.md` — Binary download guide, macOS quarantine fix (`xattr -d com.apple.quarantine netflix-narc`), `uv`/`pip` options.
- [x] **Task 2.3**: Write `docs/getting-started/exporting-netflix-csv.md` — Visual guide for downloading `ViewingHistory.csv` from Netflix Account Settings.
- [x] **Task 2.4**: Write `docs/guides/onboarding-and-setup.md` — `OnboardingScreen` wizard walkthrough & optional API key setup (CSM, OMDb, TMDB).
- [ ] **Task 2.5**: Write `docs/guides/tui-walkthrough.md` — Lineup Screen (`l`), Interrogation Room (`i`), and Preferences/Weights (`s`) guide.
- [ ] **Task 2.6**: Write `docs/guides/troubleshooting-faq.md` — CSV parsing errors, rate limit tips, config reset guide (`~/.config/netflix-narc/.env`).
- [ ] **Task 2.7**: Create `.github/workflows/docs.yml` — GitHub Actions workflow for GitHub Pages deployment using `uv run --group docs zensical build`.

### 🔴 Tier 3: High Difficulty Tasks (High-Intelligence Agents)

- [ ] **Task 3.1**: Generate & capture visual assets (high-res TUI screenshots & `vhs` recordings for Lineup & Onboarding) into `docs/assets/`.
- [ ] **Task 3.2**: Customize Zensical theme palette/CSS overrides (`docs/assets/extra.css`) to match Textual TUI dark mode theme aesthetics.
- [ ] **Task 3.3**: End-to-end verification — Execute `uv run --group docs zensical build`, check HTML output, validate all internal links and Disco search index.
- [ ] **Task 3.4**: Run full code quality suite (`uv run ruff check . --fix`, `uv run ruff format .`, `uv run mypy .`, `uv run pytest -vv`).

---

## Architecture & Technology Choice

- **Static Site Generator**: Zensical (`zensical>=0.1.0`)
- **Config Format**: `zensical.toml` (native Zensical TOML configuration for new projects)
- **Engine**: ZRX (Rust-based engine with MiniJinja template engine & Disco search engine)
- **Deployment**: GitHub Pages via `.github/workflows/docs.yml` (`uv run zensical build`)
- **Package Manager**: `uv` (using `[dependency-groups] docs` in `pyproject.toml`)

---

## Detailed Task Specifications & Code Snippets

### Step 1: Dependencies & Configuration (Tier 1)

#### [MODIFY] `pyproject.toml`

Add `docs` dependency group under `[dependency-groups]`:

```toml
[dependency-groups]
dev = [
    "invoke>=2.2.1",
    "mypy>=2.3.0",
    "pytest>=9.0.3",
    "pytest-asyncio>=0.25.3",
    "pytest-cov>=7.0.0",
    "respx>=0.22.0",
    "ruff>=0.16.2",
    "ruff-sync>=0.1.8",
]
docs = [
    "zensical>=0.1.0",
]
```

#### [NEW] `zensical.toml`

Create the project configuration in TOML format:

```toml
[project]
site_name = "netflix-narc"
site_description = "A friendly CLI/TUI tool to flag inappropriate Netflix content for families."
site_url = "https://kilo59.github.io/netflix-narc/"
repo_url = "https://github.com/Kilo59/netflix-narc"
repo_name = "Kilo59/netflix-narc"
docs_dir = "docs"
site_dir = "site"

[project.theme]
variant = "modern"
palette = [
    { media = "(prefers-color-scheme: dark)", scheme = "slate", primary = "red", accent = "amber" },
    { media = "(prefers-color-scheme: light)", scheme = "default", primary = "red", accent = "amber" }
]
features = [
    "navigation.instant",
    "navigation.tracking",
    "navigation.tabs",
    "navigation.sections",
    "navigation.top",
    "search.suggest",
    "search.highlight",
    "content.code.copy"
]

[project.markdown_extensions]
admonition = {}
"pymdownx.superfences" = {}
"pymdownx.highlight" = { anchor_linenums = true }
"pymdownx.inlinehilite" = {}
"pymdownx.tabbed" = { alternate_style = true }
"pymdownx.details" = {}
"pymdownx.emoji" = {}
attr_list = {}

[project.nav]
"Overview" = "index.md"
"Getting Started" = [
    "Installation" = "getting-started/installation.md",
    "Exporting Netflix History" = "getting-started/exporting-netflix-csv.md"
]
"User Guides" = [
    "Onboarding & Setup" = "guides/onboarding-and-setup.md",
    "TUI Feature Walkthrough" = "guides/tui-walkthrough.md",
    "Troubleshooting & FAQ" = "guides/troubleshooting-faq.md"
]
```

---

### Step 2: Task Runner & Contributing Guides (Tier 1 & Tier 2)

#### [MODIFY] `tasks.py`

Add documentation serve and build tasks:

```python
@task(
    aliases=["docs"],
    help={
        "host": "Host interface to bind (default: 127.0.0.1)",
        "port": "Port to bind (default: 8000)",
    },
)
def docs_serve(ctx: Context, host: str = "127.0.0.1", port: int = 8000) -> None:
    """Serve documentation locally using Zensical."""
    ctx.run(f"uv run --group docs zensical serve -a {host}:{port}", echo=True, pty=USE_PTY)


@task
def docs_build(ctx: Context) -> None:
    """Build documentation static site using Zensical."""
    ctx.run("uv run --group docs zensical build", echo=True, pty=USE_PTY)
```

#### [MODIFY] `CONTRIBUTING.md`

Add documentation section under Development Tasks:

```markdown
### Documentation

To preview the documentation site locally with live reloading:

```bash
uv run --group docs zensical serve
# or using invoke
uv run inv docs-serve
```

To build the static site locally:

```bash
uv run --group docs zensical build
# or using invoke
uv run inv docs-build
```
```

---

### Step 3: Core Documentation Pages (`docs/`) (Tier 2)

#### [NEW] `docs/index.md`

- Introduction to `netflix-narc` for parents and caregivers.
- Key features list: Automatic Viewing History ingest, multi-provider rating metadata (Common Sense Media, OMDb, TMDB), customizable age-appropriate safety thresholds.
- Quick navigation links to Installation and Netflix CSV Export.

#### [NEW] `docs/getting-started/installation.md`

- **Option A: Standalone Executable (Recommended for Non-Technical Users)**
  - Single-file binary download from GitHub Releases.
  - macOS installation notes (removing quarantine flag: `xattr -d com.apple.quarantine netflix-narc`).
  - Windows & Linux binary execution.
- **Option B: Using `uv` or `pip` (For Technical Users)**
  - `uv tool install netflix-narc`
  - `pip install netflix-narc`

#### [NEW] `docs/getting-started/exporting-netflix-csv.md`

- Step-by-step visual instructions:
  1. Log into [Netflix Account Activity](https://www.netflix.com/viewingactivity).
  2. Select the target child profile.
  3. Scroll to the bottom of the page and click **Download all**.
  4. Save `NetflixViewingHistory.csv` to a known folder (e.g., `Downloads`).
- Common pitfalls callout box (e.g. exporting main profile instead of child profile).

#### [NEW] `docs/guides/onboarding-and-setup.md`

- Guided walkthrough of the `OnboardingScreen` wizard.
- Setting target child age range.
- Explanation of optional API Keys (Common Sense Media, OMDb, TMDB):
  - Direct links on where to sign up for keys.
  - Clear explanation that API keys are optional and can be skipped during onboarding.

#### [NEW] `docs/guides/tui-walkthrough.md`

- **The Lineup Screen (`l`)**: Discovery Queue, severity flags (High, Med, Low), content breakdown.
- **The Interrogation Room (`i`)**: Manual data overrides, Evidence Locker offline SQLite store.
- **Preferences & Severity Weights (`s`)**: Live Weight Impact Preview, adjusting category sensitivity (Violence, Sex/Nudity, Language, Drugs, Educational Value).

#### [NEW] `docs/guides/troubleshooting-faq.md`

- "My CSV isn't loading": File format checks.
- "Rate limits exceeded": hishel caching explanation & API key tips.
- "How do I reset settings?": Path to config file (`~/.config/netflix-narc/.env`).

---

### Step 4: GitHub Actions Workflow (Tier 2)

#### [NEW] `.github/workflows/docs.yml`

```yaml
name: Deploy Documentation

on:
  push:
    branches:
      - main
    paths:
      - 'docs/**'
      - 'zensical.toml'
      - 'pyproject.toml'
      - '.github/workflows/docs.yml'
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: 'pages'
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version-file: ".python-version"

      - name: Install documentation dependencies
        run: uv sync --group docs

      - name: Build site with Zensical
        run: uv run --group docs zensical build

      - name: Upload artifact for GitHub Pages
        uses: actions/upload-pages-artifact@v3
        with:
          path: './site'

  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    needs: build
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

---

## Verification Plan

### 1. Code Quality & Format Checks

Run quality checks in order (prefix with `uv run`):

```bash
uv run ruff check . --fix
uv run ruff format .
uv run mypy .
uv run pytest -vv
```

### 2. Zensical Documentation Build Verification

Verify static site compilation:

```bash
uv run --group docs zensical build
```

Assert that:
- Exit code is `0`.
- The `site/` output directory is generated.
- `site/index.html` exists.

### 3. Local Preview Test

Serve docs locally:

```bash
uv run --group docs zensical serve
```

Verify that local web server starts on `http://127.0.0.1:8000` without errors.
