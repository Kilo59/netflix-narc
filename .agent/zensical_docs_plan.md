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
| 🟢 **Tier 1: Low** | Basic / "Dumb" Agent | `flash_lite` / `flash` | Mechanical file creation, exact config snippets (`pyproject.toml`, `tasks.py`, `CONTRIBUTING.md`, `zensical.toml`), directory creation, VHS common template creation. |
| 🟡 **Tier 2: Medium** | Standard Agent | `flash` / `pro` | Drafting structured user guides (`exporting-netflix-csv.md`, `tui-walkthrough.md`), writing GitHub Actions workflow, declarative VHS `.tape` scripts. |
| 🔴 **Tier 3: High** | High Intelligence Agent | `pro` / `high` | Visual asset capture (Textual Pilot SVG screenshot script `generate_tui_screenshots.py`), custom Zensical CSS theme matching TUI aesthetics, cross-link validation, end-to-end static site verification. |

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
- [x] **Task 2.5**: Write `docs/guides/tui-walkthrough.md` — Lineup Screen (`l`), Interrogation Room (`i`), and Preferences/Weights (`s`) guide.
- [x] **Task 2.6**: Write `docs/guides/troubleshooting-faq.md` — CSV parsing errors, rate limit tips, config reset guide (`~/.config/netflix-narc/.env`).
- [x] **Task 2.7**: Create `.github/workflows/docs.yml` — GitHub Actions workflow for GitHub Pages deployment using `uv run --group docs zensical build`.

### 🔴 Tier 3: High Difficulty Tasks (High-Intelligence Agents)

- [x] **Task 3.1**: Generate & capture visual assets (high-res SVG TUI screenshots for Lineup, Onboarding, Interrogation, and Preferences) into `docs/assets/images/`.
  - *Note*: Generated using Textual pilot native SVG renderer (`export_screenshot()`).
- [x] **Task 3.2**: Customize Zensical theme palette/CSS overrides (`docs/assets/extra.css`) to match Textual TUI dark mode theme aesthetics.
- [x] **Task 3.3**: End-to-end verification — Execute `uv run --group docs zensical build`, check HTML output, validate all internal links and Disco search index.
- [x] **Task 3.4**: Run full code quality suite (`uv run ruff check . --fix`, `uv run ruff format .`, `uv run mypy .`, `uv run pytest -vv`).

---

### 🟣 Follow-up Phase: Media Tooling & Automated Screenshots (`ruff-sync` Pattern)

Adopting the automated media generation architecture from [`Kilo59/ruff-sync`](https://github.com/Kilo59/ruff-sync).

#### 🟢 Tier 1: Low Difficulty Tasks (Basic / "Dumb" Agents)

- [ ] **Task 4.1**: Create `tapes/_common.tape` with shared Charm VHS terminal appearance config (font, theme, dimensions `1200x750`, padding).
- [ ] **Task 4.2**: Add `screenshots` (`uv run python scripts/generate_tui_screenshots.py`) and `recordings` (`vhs tapes/*.tape`) invoke tasks to `tasks.py`.
- [ ] **Task 4.3**: Update `CONTRIBUTING.md` to document `inv screenshots` and `inv recordings` developer workflows.

#### 🟡 Tier 2: Medium Difficulty Tasks (Standard Agents)

- [ ] **Task 4.4**: Create `tapes/onboarding_demo.tape` and `tapes/lineup_filtering.tape` scripts to record interactive CLI GIFs into `docs/assets/recordings/`.
- [ ] **Task 4.5**: Create mock dataset fixtures in `scripts/generate_tui_screenshots.py` to populate realistic Netflix titles and severity flags.

#### 🔴 Tier 3: High Difficulty Tasks (High-Intelligence Agents)

- [ ] **Task 4.6**: Write `scripts/generate_tui_screenshots.py` using Textual's async `run_test()` pilot to programmatically navigate screens and capture native vector SVG snapshots (`onboarding.svg`, `lineup.svg`, `interrogation.svg`, `preferences.svg`) into `docs/assets/images/`.

---

## Architecture & Technology Choice

- **Static Site Generator**: Zensical (`zensical>=0.1.0`)
- **Config Format**: `zensical.toml` (native Zensical TOML configuration for new projects)
- **Engine**: ZRX (Rust-based engine with MiniJinja template engine & Disco search engine)
- **Deployment**: GitHub Pages via `.github/workflows/docs.yml` (`uv run zensical build`)
- **Package Manager**: `uv` (using `[dependency-groups] docs` in `pyproject.toml`)
- **Screenshot Automation**: Textual Pilot (`async with app.run_test()`) saving crisp SVG files
- **Terminal Animations**: Charm VHS (`vhs tapes/*.tape`) outputting GIFs to `docs/assets/recordings/`

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

Add documentation serve, build, screenshot, and recording tasks:

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


@task
def screenshots(ctx: Context) -> None:
    """Programmatically generate SVG TUI screenshots using Textual Pilot."""
    ctx.run("uv run python scripts/generate_tui_screenshots.py", echo=True, pty=USE_PTY)


@task
def recordings(ctx: Context, tape: str | None = None) -> None:
    """Regenerate CLI animation GIFs using Charm VHS tape scripts."""
    if tape:
        ctx.run(f"vhs tapes/{tape}.tape", echo=True, pty=USE_PTY)
    else:
        ctx.run("vhs tapes/*.tape", echo=True, pty=USE_PTY)
```

---

### Step 5: Follow-up Media Tooling Specifications (`ruff-sync` Pattern)

#### [NEW] `tapes/_common.tape` (Tier 1)

```tape
# Shared VHS settings for netflix-narc documentation recordings.
Set Shell "bash"
Set FontFamily "Menlo"
Set FontSize 20
Set Width 1200
Set Height 750
Set Padding 30
Set Theme "Catppuccin Mocha"
Set TypingSpeed 50ms
Set CursorBlink false
```

#### [NEW] `scripts/generate_tui_screenshots.py` (Tier 3)

```python
"""Automated headless SVG screenshot generation for netflix-narc TUI screens."""

from __future__ import annotations

import asyncio
import pathlib
from netflix_narc.main import NetflixNarcApp

SCREENSHOTS_DIR = pathlib.Path("docs/assets/images")


async def generate_screenshots() -> None:
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    app = NetflixNarcApp()

    async with app.run_test(size=(120, 40)) as pilot:
        # Capture Lineup View
        await pilot.pause(0.5)
        app.save_screenshot(str(SCREENSHOTS_DIR / "lineup.svg"))

        # Navigate to Preferences Screen
        await pilot.press("s")
        await pilot.pause(0.3)
        app.save_screenshot(str(SCREENSHOTS_DIR / "preferences.svg"))


if __name__ == "__main__":
    asyncio.run(generate_screenshots())
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

### 2. Media Asset Generation & Zensical Build Verification

```bash
uv run python scripts/generate_tui_screenshots.py
uv run --group docs zensical build
```

Assert that:
- `docs/assets/images/*.svg` screenshots exist.
- Exit code is `0`.
- The `site/` output directory is generated.
- `site/index.html` exists.
