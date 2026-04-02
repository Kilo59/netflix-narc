# Testing Standards – netflix-narc

This document defines the mandatory testing standards and patterns for the `netflix-narc` project. AI agents MUST follow these guidelines when adding or modifying tests.

## 1. Core Principles

- **Every Fix Needs a Test**: Any bug fix must include a reproduction test that fails without the fix and passes with it.
- **No Real I/O**: Tests must never make real HTTP calls or write to the actual filesystem (outside of `tmp_path`).
- **DRY with Fixtures and Parameterization**: Avoid code duplication. Use fixtures for common setups and `@pytest.mark.parametrize` for matrix testing.
- **Explicit Dependencies**: All test dependencies must be explicit — no hidden magic.

## 2. Tooling and Environment

- **Execution**: Always run tests using `uv run pytest -vv`.
- **HTTP Mocking**: Use [respx](https://github.com/lundberg/respx) for all network interactions. Never allow real HTTP calls in tests.
- **Filesystem**: Use pytest's built-in `tmp_path` fixture for any file-based tests.

## 3. Testing Rules

### 3.1 Use Pytest Fixtures

Avoid re-defining common setup logic in every test. Use fixtures from `tests/conftest.py`.

```python
# conftest.py provides:
#   fake_settings(tmp_path)  → Settings with fake API keys, tmp cache dir
#   omdb_response_payload()  → canonical OMDb JSON dict
#   csm_response_payload()   → canonical CSM JSON dict
```

### 3.2 Parameterization

Use `@pytest.mark.parametrize` with `pytest.param(..., id="case_name")` for readable test reports.

```python
@pytest.mark.parametrize(
    "content_rating, max_age, should_flag",
    [
        pytest.param("8", 10, False, id="within-limit"),
        pytest.param("12", 10, True, id="exceeds-limit"),
        pytest.param("N/A", 10, False, id="non-numeric-rating-skipped"),
    ],
)
def test_evaluate_age_rating(content_rating, max_age, should_flag):
    ...
```

### 3.3 No Autouse Fixtures

`autouse=True` is **never allowed**. All fixtures used by a test must be explicitly declared in the test function's arguments.

### 3.4 No unittest.mock

The use of `unittest.mock` or `MagicMock` is **strictly forbidden**. Follow these patterns instead:

1. **Dependency Injection (DI)**: The API clients already accept `settings` and `cache_dir` as constructor arguments. Pass test-specific values in directly — no patching needed.
2. **`respx` for HTTP**: Use `respx.mock()` as a context manager or decorator to intercept httpx calls at the transport layer.
3. **`monkeypatch` as last resort**: Only if a dependency cannot be injected. Always prefer redesigning for DI first.

### 3.5 `if __name__` Block Required

Every test file **must** end with this block:

```python
if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
```

This enables running a single test file directly from the IDE or CLI without complex flags.

## 4. Testing API Clients (`respx` Pattern)

The `OMDBClient` and `CSMClient` accept `settings` and `cache_dir` as constructor args, making them testable without patching.

```python
import respx
import httpx
import pytest
from pydantic import SecretStr
from netflix_narc.omdb_api import OMDBClient
from netflix_narc.settings import Settings


def test_omdb_search_happy_path(tmp_path, omdb_response_payload):
    settings = Settings(omdb_api_key=SecretStr("fake-key"))

    with respx.mock:
        respx.get("http://www.omdbapi.com/").mock(
            return_value=httpx.Response(200, json=omdb_response_payload)
        )
        client = OMDBClient(settings=settings, cache_dir=tmp_path)
        result = client.search_title("The Matrix")
        client.close()

    assert result is not None
    assert result.title == "The Matrix"
    assert result.provider_name == "omdb"
```

### Key Rules for API Client Tests

- Always pass `cache_dir=tmp_path` to prevent hishel from writing to the real filesystem.
- `respx.mock()` intercepts at the `httpx` transport layer. It works with `hishel`'s `SyncCacheClient` as long as no custom `transport` is passed to the client constructor.
- If hishel returns a cached response, `respx` assertions (e.g., `assert route.called`) may not fire. Use `cache_only=False` (the default) in tests to ensure the mock is hit.

## 5. Testing the Evaluator

`evaluate_title` takes only `NormalizedMetadata` and `Settings` — pure function, no I/O. Test it directly without mocking anything.

```python
from netflix_narc.evaluator import evaluate_title
from netflix_narc.rating_api import NormalizedMetadata
from netflix_narc.settings import Settings


def test_evaluate_title_flags_age():
    settings = Settings(max_age_rating=10)
    metadata = NormalizedMetadata(
        title="Test", content_rating="12", user_rating=8.0, provider_name="test"
    )
    flags = evaluate_title(metadata, settings)
    assert any("Age rating" in f for f in flags)
```

## 6. Testing the Parser

`parse_netflix_history` reads a CSV file path. Use `tmp_path` to create test CSV files.

```python
def test_parse_netflix_history_valid_data(tmp_path):
    csv_file = tmp_path / "ViewingHistory.csv"
    csv_file.write_text("Title,Date\n\"The Matrix\",\"1/1/26\"\n", encoding="utf-8")
    records = parse_netflix_history(csv_file)
    assert len(records) == 1
```

## 7. Meta-Tests (`test_project.py`)

Project consistency tests belong in `tests/test_project.py`. Current meta-tests:

- `test_ruff_version_in_sync`: verifies the ruff version in `pyproject.toml` matches `.pre-commit-config.yaml`.

Add new meta-tests here when project-level invariants need enforcement.

## 8. Code Coverage

Target high coverage for `src/netflix_narc/`.

```bash
uv run pytest --cov=netflix_narc --cov-report=term-missing
```

> You'll need `pytest-cov` (already in dev deps). New features MUST include unit tests.
