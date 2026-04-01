# Pre-Alpha Release Checklist — `netflix-narc`

A practical, opinionated list of what to fix, add, or document before tagging `v0.1.0-alpha`.
Items are grouped by category and ordered by priority within each group.

---

## 🔴 Blockers — Must Fix

These are bugs or gaps that would confuse or break the experience for a first-time user.

### 1. `csm_api.py` is still mocked
`CSMClient.search_title` returns hardcoded dummy data regardless of the real API response.
The JSON body from the API is fetched but never parsed (`response.json()` result is discarded).
**Fix**: Parse the real CSM JSON shape into `NormalizedMetadata`, or clearly gate the provider behind a feature flag and hide it from the `SetupScreen` until it's real.

### 2. CSV path is hardcoded
`action_load_csv` (line 202) and `main()` (line 282) both hardcode `"NetflixViewingHistory.csv"`.
A user whose file is elsewhere gets an opaque `FileNotFoundError` notification.
**Fix**: Either open a native file-picker dialog (Textual's `DirectoryTree` / `FileOpen` widget) or accept the path as a CLI argument via `argparse`/`typer`.

### 3. `.env` persistence is append-only and fragile
`handle_setup_complete` appends new keys to `.env` every time the user presses "Save & Continue", with no deduplication. Keys accumulate silently.
**Fix**: Read the existing `.env`, replace the relevant line(s) in-place, and rewrite atomically.

### 4. API key leaked in URL query params (OMDb)
`omdb_api.py` sends the API key as a `params={"apikey": ...}` query parameter. This key ends up in the hishel SQLite cache URL column in plaintext.
**Fix**: Pass the key in an `Authorization` or `X-API-Key` header so it is not stored in cache logs. (OMDb does support `?apikey=` officially, but document the risk or use request post-processing to strip it from the cached URL.)

### 5. `pyproject.toml` description placeholder
```toml
description = "Add your description here"
```
**Fix**: Write a real one-liner before publishing. e.g. `"A terminal UI that narcs on inappropriate Netflix viewing history."`.

---

## 🟠 UX Issues — High Value, Low Effort

### 6. `DetailsSidebar` is display-only (dead UI)
The sidebar shows `Violence Weight: High` as a hardcoded string. Settings have no effect on what's displayed and there's no way to edit weights from the UI.
**Fix (minimal)**: Either make the sidebar reactive (bind to `Settings.weights`) or remove it for the pre-alpha and add it back as a proper interactive widget in v0.2.

### 7. Evaluation blocks the main thread
`rebuild_table` calls `self.rating_provider.search_title(...)` synchronously inside the Textual event loop. For 200 titles this will freeze the UI.
**Fix**: Move evaluation into a `worker` thread (`self.run_worker(...)`) and update the table progressively as results come in.

### 8. No visual feedback during evaluation
The user presses `e`, sees a brief notification, and then stares at a potentially frozen table.
**Fix**: Add a `LoadingIndicator` or progress bar while the worker runs.

### 9. `on_mount` silently swallows startup errors
If `get_rating_provider` raises inside `on_mount`, the `except` clause shows a notification but the app continues in a broken state (no provider, no data).
**Fix**: Either present the `SetupScreen` automatically on mount when `rating_provider` is `None`, or show a persistent banner indicating setup is needed.

---

## 🟡 Code Quality / Architecture

### 10. `evaluator.py` MPAA rating logic is a no-op
The age-rating check silently skips any non-numeric string (`PG-13`, `TV-MA`, `R`, etc.) with a bare `except`. For OMDb — the recommended provider — this means the age check *never fires*.
**Fix**: Add an MPAA/TV rating mapping (e.g. `{"G": 0, "PG": 8, "PG-13": 13, "R": 17, "NC-17": 18, "TV-Y": 2, ...}`) so the age check works for both CSM and OMDb.

### 11. `RatingProvider` protocol `close()` is never called
Providers open an `httpx` client on init but `close()` is never called in `main.py`.
**Fix**: Add `on_unmount` → `self.rating_provider.close()` to `NetflixNarcApp`, or implement `__enter__`/`__exit__` and use a context manager.

### 12. `rebuild_table` re-evaluates everything on every expand/collapse
Toggling a row calls `rebuild_table(evaluate=False)`, but the full loop still runs over all `grouped_records`. For large histories this will cause jank.
**Fix**: Use `table.add_row`/`table.remove_row` targeted on just the toggled section.

### 13. `version = "0.1.0.dev0"` — pin before tagging
When you cut the release, bump to `0.1.0a1` (PEP 440 pre-release) and tag it.

---

## 🟢 Testing Gaps

### 14. No tests for `main.py` / TUI
The `App` is currently completely untested. Add at minimum a smoke-test using `App.run_test()` (Textual's async test driver) that asserts the app mounts, the table appears, and the `SetupScreen` is reachable.

### 15. No tests for the CSM client's real response parsing
`test_csm_search_happy_path` respx-mocks a request and then the client discards the response body anyway (bug #1 above). Once parsing is implemented the test fixture in `conftest.py` (`csm_response_payload`) should drive the actual assertion.

### 16. No tests for `factory.py`
`get_rating_provider` has no test coverage. Add parametrized tests asserting the correct class is returned for each `RatingProviderType` and that a `ValueError` is raised when the matching key is missing.

### 17. No test for `.env` persistence logic
The file-writing code in `handle_setup_complete` writes secrets to disk. Add a test using `tmp_path` to verify the key appears and is not duplicated on a second save.

---

## 📄 Documentation

### 18. `README.md` installation instructions require cloning
"Clone the repository" is the only path. Pre-alpha users should be able to do `uvx netflix-narc` or `uv tool install netflix-narc`.
**Fix**: Add a one-command install option (even if it's just `uv tool install git+https://github.com/Kilo59/netflix-narc`) alongside the dev-path instructions.

### 19. README missing a screenshot / demo GIF
The `hero.png` exists in `assets/` but there's no terminal screenshot showing the actual TUI at runtime. Pre-alpha adopters want to see what they're getting.
**Fix**: Add an `asciinema` cast or a cropped screenshot of the running TUI to `assets/` and embed it in the README.

### 20. `CHANGELOG.md` — start one
A conventional-commits-style changelog entry for `v0.1.0-alpha` signals professionalism and gives future contributors a baseline.
**Fix**: Create `CHANGELOG.md` with an `[Unreleased]` section and an initial `[0.1.0-alpha]` block listing key features.

### 21. `implementation_plan.md` and `api_evaluation.md` are in the repo root
These are internal planning artifacts that shouldn't ship to end users.
**Fix**: Move them to `.agent/` or add them to `.gitignore`. At minimum, add a note in `README.md` that they are internal design docs.

### 22. Missing `CONTRIBUTING.md`
For a pre-alpha release, tell potential contributors: how to set up the dev environment (`uv sync`), how to run the tests, and what the `pre-commit` hooks enforce.

---

## ⚙️ CI / Release Hygiene

### 23. No CI pipeline
There is a `.pre-commit-config.yaml` but no GitHub Actions workflow. First-time contributors will have no safety net.
**Fix**: Add `.github/workflows/ci.yml` that runs `ruff check`, `mypy`, and `pytest` on every push/PR (use `uv run` throughout).

### 24. No release workflow
**Fix**: Add `.github/workflows/release.yml` triggered on `push: tags: ['v*']` that builds the `sdist/wheel` with `uv build` and publishes to PyPI (or just creates a GitHub Release artifact for now).

### 25. `NetflixViewingHistory.csv` is committed to the repo
This is personal viewing history and should not be in the git history.
**Fix**: Add it to `.gitignore` immediately. Consider rotating it out of git history with `git filter-branch` or BFG if it contains real private data.

---

## Summary Table

| Priority | Count | Theme |
|---|---|---|
| 🔴 Blocker | 5 | Mocked API, hardcoded CSV path, broken `.env` write, API key in cache, placeholder description |
| 🟠 UX | 4 | Dead sidebar, blocking evaluation, no progress feedback, silent startup failure |
| 🟡 Code | 4 | MPAA mapping missing, resource leak, rendering perf, version bump |
| 🟢 Tests | 4 | TUI smoke test, CSM parsing, factory, `.env` write |
| 📄 Docs | 5 | Install UX, screenshot, CHANGELOG, artifact cleanup, CONTRIBUTING |
| ⚙️ CI | 3 | CI pipeline, release workflow, remove CSV from repo |

**Minimum viable pre-alpha** (to be usable with OMDb): blockers #2, #3, #5; UX issues #7, #9; code fix #10; CI item #25.

---

## ✅ Task Checklist by Agent Complexity

Complexity levels are assigned by the scope of reasoning required:
- **🟢 Low** — Mechanical, well-defined, single file or config change. Safe for basic/dumb agents with minimal context.
- **🟡 Medium** — Requires reading 2–4 source files and following established patterns. Suitable for mid-tier agents given clear specs.
- **🔴 High** — Requires architectural understanding, multiple interacting files, or Textual/async internals. Requires a smart agent or human review.

---

### 🟢 Low Complexity
> Single-file or config-only changes. Fully mechanical. Provide the file path and the fix — agent needs no broader context.

- [x] **#5** — Fix `pyproject.toml` description placeholder → set `description = "A terminal UI that narcs on inappropriate Netflix viewing history."`
- [x] **#13** — Bump version in `pyproject.toml` from `0.1.0.dev0` → `0.1.0a1`
- [x] **#20** — Create `CHANGELOG.md` with an `[Unreleased]` section and an initial `[0.1.0-alpha]` block *(template-based, no code reading required)*
- [x] **#21** — Move `implementation_plan.md` and `api_evaluation.md` from repo root into `.agent/`; add both to `.gitignore`
- [x] **#25** — Add `NetflixViewingHistory.csv` to `.gitignore` and run `git rm --cached NetflixViewingHistory.csv`
- [x] **#11** — Add `on_unmount` → `self.rating_provider.close()` to `NetflixNarcApp` in `main.py` *(2-line change, clear spec)*

---

### 🟡 Medium Complexity
> Requires reading a few source files and understanding existing patterns. Agent needs the relevant module(s) as context.

- [ ] **#3** — Fix `.env` persistence in `handle_setup_complete` (`main.py`): read existing `.env`, replace matching key lines in-place, rewrite atomically using `pathlib`
- [ ] **#10** — Add MPAA/TV rating → age integer mapping to `evaluator.py` so the age-rating check fires for OMDb results (e.g. `{"PG-13": 13, "R": 17, "TV-MA": 18, ...}`)
- [ ] **#16** — Add parametrized tests for `factory.py` in a new `tests/test_factory.py`: assert correct provider class per `RatingProviderType`, assert `ValueError` on missing key
- [ ] **#17** — Add test for `.env` write/deduplication logic using `tmp_path` (depends on #3 being implemented first)
- [ ] **#22** — Create `CONTRIBUTING.md` covering: `uv sync`, `uv run pytest`, `uv run ruff check`, `pre-commit install`, and branch/PR conventions
- [ ] **#23** — Add `.github/workflows/ci.yml` running `ruff check`, `mypy`, and `pytest` on push/PR with `uv run` *(standard GHA pattern, no app knowledge needed)*
- [ ] **#24** — Add `.github/workflows/release.yml` triggered on `v*` tags, running `uv build` and uploading artifacts to a GitHub Release
- [ ] **#6** — Remove the `DetailsSidebar` widget and its placeholder `Static` items from `main.py` and `narc.tcss` for the pre-alpha; leave a `# TODO: v0.2` comment

---

### 🔴 High Complexity
> Requires deep understanding of Textual's async/worker model, hishel internals, or cross-file architectural changes. Use a smart agent with full project context, or do it yourself.

- [ ] **#1** — Implement real CSM JSON response parsing in `csm_api.py`: map `data[0].age` → `content_rating`, `data[0].rating * 2` → `user_rating`, `data[0].categories` → `category_scores`; update `test_csm_search_happy_path` to assert parsed fields
- [ ] **#2** — Fix hardcoded CSV path: add `--csv` CLI argument to `main()` via `argparse` *and/or* integrate Textual's `FileOpen` dialog into `action_load_csv`. Touches `main.py`, `main()` entrypoint, and `README.md`.
- [ ] **#4** — Prevent OMDb API key appearing in hishel's SQLite cache: move the key into a request header via an `httpx.Auth` subclass or post-process cached URLs to strip query params
- [ ] **#7** — Move title evaluation off the main thread using Textual's `@work` decorator / `run_worker`; update rows progressively as workers complete; coordinate state with `self.evaluated_flags` safely
- [ ] **#8** — Add a `LoadingIndicator` or `ProgressBar` to the TUI that is visible during evaluation and hidden when all workers finish *(depends on #7)*
- [ ] **#9** — Auto-present `SetupScreen` on mount when `rating_provider` is `None` after initial settings load; ensure the app doesn't proceed to an unusable state silently
- [ ] **#12** — Optimize expand/collapse in `on_data_table_row_selected`: instead of calling `rebuild_table()`, surgically insert/remove child rows adjacent to the toggled parent row using the DataTable API
- [ ] **#14** — Add async TUI smoke tests in `tests/test_main.py` using Textual's `App.run_test()` context manager: assert app mounts, table is visible, and `SetupScreen` is reachable via `action_settings`
- [ ] **#15** — Once #1 is complete, update `test_csm_search_happy_path` to use `csm_response_payload` fixture and assert all `NormalizedMetadata` fields are correctly mapped
- [ ] **#18** — Add `uv tool install git+https://github.com/Kilo59/netflix-narc` install path to `README.md`; audit `pyproject.toml` for any packaging gaps (`classifiers`, `license`, `urls`) needed for PyPI-readiness
- [ ] **#19** — Capture a terminal screenshot of the running TUI (using `vhs`, `asciinema`, or a manual screenshot), add to `assets/screenshot.png`, and embed in `README.md`
