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

## Pull Request Guidelines

1.  **Create a branch**: Use descriptive names like `feat/add-tmdb-provider` or `fix/csv-parsing-bug`.
2.  **Add tests**: Every new feature or fix must include unit tests. Use `tmp_path` for file operations and `respx` for network mocking.
3.  **Validate**: Ensure all linting, formatting, type checking, and tests pass before submitting.
4.  **Changelog**: Add a brief entry to the `[Unreleased]` section of `CHANGELOG.md`.

## Project Structure

- `src/netflix_narc/`: Core application logic.
- `tests/`: Unit and integration tests.
- `.agent/`: Internal design and planning documents.
- `assets/`: Images, screenshots, and visual assets.
