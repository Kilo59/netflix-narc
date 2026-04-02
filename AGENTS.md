## Project Overview

**netflix-narc** is a CLI/TUI application that ingests a Netflix viewing history CSV, fetches title metadata and age ratings from external APIs (Common Sense Media, OMDb, TMDB), and flags inappropriate content based on customizable, weighted criteria.

- **GitHub Repository**: [`Kilo59/netflix-narc`](https://github.com/Kilo59/netflix-narc)
- The application uses a `src` layout in `src/netflix_narc/`.
- Dev dependencies are managed with [uv](https://docs.astral.sh/uv/).

## GitHub Context

This is a GitHub-hosted project. Use the **`gh` CLI** to gather extra context about issues, pull requests, and releases before starting work.

```bash
# Issues
gh issue list                      # Open issues
gh issue view <number>             # Read a specific issue with full context

# Pull Requests
gh pr list                         # Open PRs
gh pr view <number>                # Read PR description, review comments, checks
gh pr checks <number>              # See CI status for a PR
```

## Tech Stack

- **Python** ≥ 3.13
- **Package Manager**: [uv](https://docs.astral.sh/uv/) — Use `uv run <command>` for all executions.
- **TUI Framework**: [Textual](https://textual.textualize.io/) (`>=8.1.1`)
- **HTTP Client**: [httpx](https://www.python-httpx.org/) (sync, via hishel)
- **HTTP Caching**: [hishel](https://hishel.com/) — CRITICAL for API rate limits. See `.agents/skills/hishel/SKILL.md`.
- **Configuration**: [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- **Data Models**: pydantic (`BaseModel`, `SecretStr`)
- **Linter / Formatter**: [Ruff](https://docs.astral.sh/ruff/) (`>=0.15.5`)
- **Type Checker**: [mypy](https://mypy-lang.org/) (strict mode)
- **Test Framework**: [pytest](https://docs.pytest.org/) with `respx` (See [Testing Standards](.agents/TESTING.md))

## Project Structure

```text
.agent/                         # Design docs (architecture, API design, plan)
  architecture.md
  design.md
  plan.md
.agents/                        # Agent-specific instructions
  TESTING.md                    # Mandatory testing patterns and rules
  workflows/                    # Step-by-step guides for common tasks
    add-test-case.md
  skills/
    hishel/SKILL.md             # How to use the hishel caching library
    textual/SKILL.md            # How to use the Textual TUI framework
src/netflix_narc/
  parser.py                     # Parses ViewingHistory.csv
  csm_api.py                    # Common Sense Media API client (hishel cached)
  omdb_api.py                   # OMDb API client (hishel cached)
  factory.py                    # Instantiates the correct RatingProvider
  evaluator.py                  # Applies user weights to NormalizedMetadata
  rating_api.py                 # RatingProvider Protocol + NormalizedMetadata model
  settings.py                   # pydantic-settings config (API keys, thresholds)
  main.py                       # Textual TUI entrypoint
tests/
  conftest.py                   # Shared fixtures (fake_settings, response payloads)
  test_evaluation.py            # Unit tests for evaluator.py
  test_parser.py                # Unit tests for parser.py
  test_rating_api.py            # HTTP-mocked tests for API clients (respx)
  test_project.py               # Meta-tests (config consistency checks)
```

After ANY code change, validate with the following tools in this order. **ALWAYS prefix with `uv run`**:

### 1. Lint with Ruff

```bash
uv run ruff check . --fix
```

- Do NOT disable rules or add `# noqa` directives unless the user explicitly asks. Fix the underlying code.
- To understand a rule: `uv run ruff rule <RULE_CODE>`

### 2. Format with Ruff

```bash
uv run ruff format .
```

### 3. Type-check with mypy

```bash
uv run mypy .
```

- mypy runs in strict mode (`python_version = "3.13"`).
- Tests have relaxed rules (`type-arg` and `no-untyped-def` are disabled for `tests.*`).

### 4. Run Tests

```bash
uv run pytest -vv
```

## Imports

- Always use `from __future__ import annotations` as the first import in every Python file.
- Use `import pathlib` (not `from pathlib import Path`) and `import datetime as dt` (not `from datetime import ...`).
- **Do NOT use `unittest.mock` or `MagicMock`**. Prefer Dependency Injection (DI) and dedicated IO-layer libraries (`respx` for HTTP, `tmp_path` for filesystem). See `.agents/TESTING.md`.
- Imports used only for type hints go inside `if TYPE_CHECKING:` blocks.

## Style

- Use `pathlib` over `os.path` (enforced by `PTH` rules).
- **Prefer `typing.Protocol` over `abc.ABC`** for abstract base classes — already in use via `RatingProvider`.
- **Prefer Dependency Injection (DI)**: Pass dependencies (settings, cache_dir) as arguments. This is what makes the API clients testable without patching.
- Use `pydantic` models for all structured data. Avoid passing raw untyped `dict` objects.
- Do not use `@pytest.fixture(autouse=True)`. All fixtures must be explicitly requested.

## Architecture Rules

1. **Never mock hishel's cache logic**: When testing `csm_api.py` or `omdb_api.py`, pass a `tmp_path`-based `cache_dir` to the client constructor. This keeps the cache functional but sandboxed.
2. **Onboarding First**: If `Settings` cannot find the API key for the active provider, the TUI MUST intercept and present an onboarding view.
3. **Dependency restraint**: Do not add heavy parsing libraries (e.g., `pandas`). Use standard library + pydantic.
4. **Strict Typing**: Use Python 3.13 features. Always prefer typed pydantic models or `TypedDict` over raw dicts.

## Testing

See [`.agents/TESTING.md`](.agents/TESTING.md) for the full mandatory testing guide.

Key rules:
- No real HTTP calls in tests — use `respx`.
- No real filesystem writes outside `tmp_path`.
- No `unittest.mock` or `MagicMock`.
- No `autouse=True` fixtures.
- Every test file must end with `if __name__ == "__main__": pytest.main([__file__, "-vv"])`.

## Common Pitfalls

1. **hishel cache writes**: The `SyncCacheClient` will write to disk. In tests, always pass `cache_dir=tmp_path` to the client constructor to keep cache writes sandboxed.
2. **respx + hishel**: `respx.mock()` intercepts at the `httpx` transport layer and works with `hishel`'s `SyncCacheClient` as long as no custom `transport` is passed to the client. Do not add a custom transport without also updating the test strategy.
3. **SecretStr in tests**: `pydantic.SecretStr` cannot be created directly from an env var in tests. Use `Settings(omdb_api_key=SecretStr("fake"), _env_file=None)` — or use the `fake_settings` fixture from `conftest.py`.
4. **`content_rating` is a string**: The CSM API returns age ratings as integers (e.g., `8`), but `NormalizedMetadata.content_rating` is `str | None`. The client converts with `str(int_val)`. The evaluator parses back with `int()`. Keep this conversion chain in mind.
5. **Ruff version sync**: The ruff version in `pyproject.toml` must stay in sync with `.pre-commit-config.yaml`. The test `test_ruff_version_in_sync` in `tests/test_project.py` enforces this.
