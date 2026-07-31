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

When preparing a new release for PyPI and GitHub:

1. **Verify Local Quality Checks**:
   Ensure all checks pass locally:
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
   - Move entries from `[Unreleased]` to a new version header with today's date (e.g. `## [0.1.0] - YYYY-MM-DD`).
   - Add a fresh empty `## [Unreleased]` section at the top.

4. **Verify Build Package**:
   Test building the wheel and source distribution:
   ```bash
   uv build
   ```

5. **Commit and Tag**:
   Commit the version bump and create an annotated git tag prefixed with `v`:
   ```bash
   git commit -am "chore: release v0.1.0"
   git tag -a v0.1.0 -m "Release v0.1.0"
   ```

6. **Push Tag to Trigger Publishing**:
   Push the main branch and the release tag to GitHub:
   ```bash
   git push origin main --tags
   ```

7. **Automated CI/CD Release**:
   Pushing a `v*` tag triggers the [.github/workflows/release.yml](file:///.github/workflows/release.yml) GitHub Actions workflow, which will automatically:
   - Build the package distribution using `uv build`.
   - Publish the artifacts to [PyPI](https://pypi.org/project/netflix-narc/) via PyPI Trusted Publishing.
   - Create a GitHub Release with dist assets and generated release notes.
