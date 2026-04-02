---
description: How to add a new test case for a rating API provider
---

Follow these steps to add a new test case for a `RatingProvider` (e.g., `OMDBClient`, `CSMClient`, or a future provider).

### 1. Identify What to Test

Clearly define:
- **Which client** is being tested (`OMDBClient`, `CSMClient`, etc.)
- **What input** triggers the behavior (a specific API response shape, HTTP status code, or edge-case field value)
- **What output** is expected (`NormalizedMetadata`, `None`, or a raised exception)

### 2. Add the Test to the Right File

| Scenario | Target file |
|---|---|
| Happy path / API response parsing | `tests/test_rating_api.py` |
| Evaluator logic (flags, weights) | `tests/test_evaluation.py` |
| CSV parser edge case | `tests/test_parser.py` |
| Project config consistency | `tests/test_project.py` |

### 3. Write the Test Using `respx`

Use `respx.mock` to intercept HTTP calls. Always pass `cache_dir=tmp_path` to the client.

```python
def test_omdb_returns_none_on_false_response(tmp_path, fake_settings):
    payload = {"Response": "False", "Error": "Movie not found!"}

    with respx.mock:
        respx.get("http://www.omdbapi.com/").mock(
            return_value=httpx.Response(200, json=payload)
        )
        client = OMDBClient(settings=fake_settings, cache_dir=tmp_path)
        result = client.search_title("Nonexistent Movie")
        client.close()

    assert result is None
```

### 4. Use the `fake_settings` Fixture

Always use the `fake_settings` fixture from `conftest.py`. Never use a real `.env` file or real API keys in tests.

```python
def test_my_new_case(tmp_path, fake_settings):
    ...
```

### 5. Use `@pytest.mark.parametrize` for Variants

// turbo
If you're testing multiple similar variants of the same scenario, use parametrize:

```bash
# After writing the test, run:
uv run pytest -vv tests/test_rating_api.py
```

### 6. Validate Formatting and Types

// turbo
```bash
uv run ruff check . --fix
uv run ruff format .
uv run mypy .
```

### 7. Run the Full Test Suite

// turbo
```bash
uv run pytest -vv
```

All tests must pass before committing.
