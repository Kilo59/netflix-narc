# Design & Architecture Decisions (ADR)

This document tracks significant technical decisions, trade-offs, and design patterns adopted during development.

---

## 1. Async Background Evaluation
**Date**: 2026-04-01
**Context**: Rebuilding the large data table during title evaluation (which involves sequential API calls) blocked the main TUI thread, causing the UI to hang.
**Decision**:
- Move evaluation logic into a dedicated background worker thread using `run_worker(thread=True)`.
- Use `functools.partial` to pass arguments to the worker instead of relying on the (private) `@work` decorator.
- Implement progressive UI updates: the worker calls `self.call_from_thread(self._update_row_flags, ...)` as each title finishes.
- Added a `LoadingIndicator` docked to the bottom to signal activity.
**Trade-off**: Increases state management complexity (e.g., handling table rebuilds while workers are still running).

## 2. OMDb API Key Cache Risk
**Date**: 2026-04-01
**Context**: `hishel` (HTTP cache) stores the full request URL in its SQLite database. OMDb uses an `apikey` query parameter, meaning the secret key is written to the local cache file in plain text.
**Decision**:
- Accepted the risk for `v0.1-alpha`. The cache is a local file (`~/.cache/...`) with user-only permissions.
- Documented the risk clearly in `tests/test_rating_api.py`.
- Planned fix for `v0.2`: Implement a custom `hishel` storage backend or a `SecretStripper` transport to scrub keys before they hit the disk.
**Rationale**: Implementing a custom cache storage backend was deemed too high-complexity for the initial pre-alpha milestone.

## 3. Standardized TUI Testing
**Date**: 2026-04-01
**Context**: Manual testing of TUI screens (Setup, Error handling) is slow and error-prone.
**Decision**:
- Adopted Textual's `App.run_test()` async context manager for "smoke tests".
- Integrated `pytest-asyncio` with `asyncio_mode = "auto"` in `pyproject.toml` to handle the async generators seamlessly.
- Prioritized "structural" tests: verifying widget presence and screen stack transitions (e.g., pressing 's' pushes `SetupScreen`).

## 4. CSM API Mapping Layer
**Date**: 2026-04-01
**Context**: The Common Sense Media (CSM) API returns complex nested JSON with snake_case keys and varying scales (e.g., 1-5 stars).
**Decision**:
- Implemented a rigorous mapping layer in `CSMClient.search_title`.
- Normalized 1-5 scale quality ratings to the internal 0-10 scale.
- Mapped granular category keys (e.g. `violence`) to canonical display strings (e.g. `Violence & Scariness`) at the source.
**Rationale**: Keeps the `evaluator.py` and TUI logic agnostic of specific API quirks.

## 5. PyPI Readiness & `uv` Tooling
**Date**: 2026-04-01
**Context**: We want users to be able to install the app easily without cloning.
**Decision**:
- Added formal `project.urls`, `classifiers`, and `license` to `pyproject.toml`.
- Promoted `uv tool install git+https://github.com/Kilo59/netflix-narc` as the primary installation method in `README.md`.
- Specified `textual >= 8.1.1` to ensure availability of modern worker and screen APIs.

## 6. Avoiding Private Framework APIs
**Date**: 2026-04-01
**Context**: Textual's `@work` decorator was found to be in a private module (`_work_decorator`) in some versions.
**Decision**:
- Reverted to using `self.run_worker(functools.partial(func, *args), ...)` in `main.py`.
**Rationale**: Minimizes risk of breakage on minor framework updates.
