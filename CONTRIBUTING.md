# Contributing to Netflix Narc

Thank you for your interest in contributing to `netflix-narc`! This project provides a TUI to help users evaluate their Netflix viewing history against content criteria.

## Local Setup

We use [uv](https://docs.astral.sh/uv/) for package management and environment isolation.

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/Kilo59/netflix-narc.git
    cd netflix-narc
    ```

2.  **Synchronize dependencies**:
    ```bash
    uv sync
    ```

3.  **Install pre-commit hooks**:
    ```bash
    uv run pre-commit install
    ```

4.  **(Optional) Install Rust for local binary builds**:
    If you want to test building standalone executables locally via `uv run invoke build-binary`, ensure the Rust toolchain (`cargo`) is installed:
    ```bash
    # Install via rustup (recommended)
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
    # Or via Homebrew on macOS
    brew install rust
    ```

## Development Workflow

### Running the Application

You can run the application directly using `uv run`:

```bash
uv run netflix-narc
```

To provide a specific CSV path:

```bash
uv run netflix-narc --csv path/to/your/ViewingHistory.csv
```

### Running Tests

We use `pytest` for unit testing and `respx` for HTTP mocking.

```bash
uv run pytest -vv
```

To run with coverage:

```bash
uv run pytest --cov=netflix_narc --cov-report=term-missing
```

### Linting and Formatting

We use `Ruff` for both linting and formatting.

```bash
# Check for linting issues
uv run ruff check .

# Fix linting issues (where possible)
uv run ruff check . --fix

# Format code
uv run ruff format .
```

### Type Checking

We use `mypy` in strict mode.

```bash
uv run mypy .
```

## Release Process & Versioning Strategy

This project follows [Semantic Versioning (SemVer 2.0.0)](https://semver.org/spec/v2.0.0.html) and uses PEP 440 compliant version strings (e.g., `0.1.0a1`, `0.1.0`, `1.0.0`).

### Versioning Rules

- **Pre-releases (`0.1.0a1`, `0.1.0b1`, `0.1.0rc1`)**: Use alpha (`aN`), beta (`bN`), or release candidate (`rcN`) suffixes while features are stabilizing or in pre-alpha/alpha status.
- **Patch releases (`x.y.Z`)**: Bug fixes, non-breaking performance updates, or dependency bumps that maintain backward compatibility.
- **Minor releases (`x.Y.0`)**: New features, new rating providers, or new UI components added in a backward-compatible manner.
- **Major releases (`X.0.0`)**: Breaking changes to CLI options, settings schemas, or sync protocols.

### Release Steps

Releasing `netflix-narc` follows a structured two-phase process:

#### Phase 1: Pre-Release Preparation (Artifacts on `main`)

1. **Verify Local Quality Checks**:
   Ensure all quality checks pass locally before making release edits:
   ```bash
   uv run ruff check .
   uv run ruff format --check .
   uv run mypy .
   uv run pytest -vv
   ```

2. **Bump Version Number**:
   Use `uv version` to bump the project version in `pyproject.toml` (e.g. `uv version patch`, `uv version minor`, `uv version 0.1.0`):
   ```bash
   uv version minor
   # or explicitly:
   uv version 0.1.0
   ```

3. **Update `CHANGELOG.md`**:
   - Move all completed entries under `## [Unreleased]` into a new version header with today's date (e.g., `## [0.1.0] - YYYY-MM-DD`).
   - Add a fresh empty `## [Unreleased]` section at the top of the file.

4. **Commit & Push Changes to `main`**:
   Commit the version bump and `CHANGELOG.md` updates, and ensure all release artifacts exist on `main` prior to tagging:
   ```bash
   git commit -am "chore: release vX.Y.Z"
   git push origin main
   ```

---

#### Phase 2: Tagging, CI Release Publishing & Post-Release Narrative

1. **Tag the Release Commit on `main`**:
   Create an annotated git tag prefixed with `v` on the latest `main` commit containing the release artifacts:
   ```bash
   git checkout main
   git pull origin main
   git tag -a vX.Y.Z -m "Release vX.Y.Z"
   ```

2. **Push Tag to Trigger CI Publishing**:
   Push `main` and the release tag to GitHub to trigger the automated release pipeline:
   ```bash
   git push origin main --tags
   ```

3. **Automated CI/CD Release Execution**:
   Pushing a `v*` tag triggers the [.github/workflows/release.yml](file:///.github/workflows/release.yml) GitHub Actions workflow, which automatically:
   - Builds the wheel & sdist distribution packages using `uv build`.
   - Compiles standalone zero-dependency executables via **PyApp** for **macOS Apple Silicon** (`aarch64-apple-darwin`), **macOS Intel** (`x86_64-apple-darwin`), **Linux** (`x86_64-unknown-linux-gnu`), and **Windows** (`x86_64-pc-windows-msvc.exe`).
     PyApp's dependency crates are cached between runs using [`sccache`](https://github.com/mozilla/sccache) (see `pre-publish` job in `.github/workflows/ci.yml`). Only the final `pyapp` crate recompiles on each run to embed the freshly built wheel.
   - Publishes the wheel package to [PyPI](https://pypi.org/project/netflix-narc/) via Trusted Publishing.
   - Creates a GitHub Release with all pre-compiled standalone binary executables and wheels attached.

4. **Post-Release Narrative Update**:
   Once the automated GitHub Release is created by CI:
   - Edit the GitHub Release (via GitHub Web UI or `gh release edit vX.Y.Z`).
   - Add a high-level narrative summary providing release highlights, architectural updates, screenshots/media, and upgrade guidance beyond raw `CHANGELOG.md` bullet points.
