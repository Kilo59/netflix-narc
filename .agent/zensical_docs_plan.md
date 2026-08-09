# Implementation Plan — Zensical Documentation Site Setup & User Guides

Resolves Issue: [#27](https://github.com/Kilo59/netflix-narc/issues/27)
Context Reference: [`ruff-sync#141`](https://github.com/Kilo59/ruff-sync/issues/141)

## Goal

Build a modern, user-friendly, and media-rich documentation site for **netflix-narc** using **Zensical** (the high-performance, Rust-powered successor to Material for MkDocs).

Because `netflix-narc` targets non-technical users (parents, guardians, caregivers monitoring family viewing habits), this documentation site prioritizes visual clarity, step-by-step guidance, annotated screenshots, and terminal UI recordings over dense technical API/CLI reference specs.

---

## Architecture & Technology Choice

- **Static Site Generator**: Zensical (`zensical>=0.1.0`)
- **Config Format**: `zensical.toml` (native Zensical TOML configuration for new projects)
- **Engine**: ZRX (Rust-based engine with MiniJinja template engine & Disco search engine)
- **Deployment**: GitHub Pages via `.github/workflows/docs.yml` (`uv run zensical build`)
- **Package Manager**: `uv` (using `[dependency-groups] docs` in `pyproject.toml`)

---

## Proposed Changes

```text
pyproject.toml                            # [MODIFY] Add dependency-groups.docs
tasks.py                                  # [MODIFY] Add docs_serve & docs_build invoke tasks
CONTRIBUTING.md                           # [MODIFY] Add local documentation build instructions
zensical.toml                             # [NEW] Native Zensical configuration file
.github/workflows/docs.yml                # [NEW] CI workflow for GitHub Pages deployment
docs/
  index.md                                # [NEW] Landing page & quick intro for parents
  getting-started/
    installation.md                       # [NEW] Installation guide (Binary, uv, pip)
    exporting-netflix-csv.md              # [NEW] Step-by-step Netflix CSV export guide
  guides/
    onboarding-and-setup.md               # [NEW] Onboarding wizard & API keys guide
    tui-walkthrough.md                    # [NEW] TUI Lineup, Interrogation Room & Settings guide
    troubleshooting-faq.md                # [NEW] Common errors, FAQ & config resets
  assets/
    images/                               # [NEW] Directory for screenshots and SVGs
    recordings/                           # [NEW] Directory for terminal UI recordings / GIFs
```

---

### Step 1: Dependencies & Configuration

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

### Step 2: Task Runner & Contributing Guides

#### [MODIFY] `tasks.py`

Add documentation serve and build tasks:

```python
@task(
    aliases=["docs"],
    help={"host": "Host interface to bind (default: 127.0.0.1)", "port": "Port to bind (default: 8000)"},
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

### Step 3: Core Documentation Pages (`docs/`)

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

### Step 4: GitHub Actions Workflow

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

## Detailed Step-by-Step Execution for Agents

Follow these steps strictly in order:

### 1. Update `pyproject.toml`
Add the `docs = ["zensical>=0.1.0"]` dependency group to `pyproject.toml`.
Run:
```bash
uv lock
uv sync --group docs
```

### 2. Create `zensical.toml`
Create `zensical.toml` at the repository root with the exact TOML structure defined above.

### 3. Add `tasks.py` and `CONTRIBUTING.md` Entries
Update `tasks.py` to include `docs_serve` and `docs_build`.
Update `CONTRIBUTING.md` with documentation commands.

### 4. Create Documentation Pages in `docs/`
Create directory `docs/`, `docs/getting-started/`, `docs/guides/`, `docs/assets/images/`, `docs/assets/recordings/`.
Create all 6 markdown files (`index.md`, `getting-started/installation.md`, `getting-started/exporting-netflix-csv.md`, `guides/onboarding-and-setup.md`, `guides/tui-walkthrough.md`, `guides/troubleshooting-faq.md`).

### 5. Create `.github/workflows/docs.yml`
Create the GitHub Actions workflow file with Pages deployment steps.

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
