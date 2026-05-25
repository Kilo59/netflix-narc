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

## 7. XDG Config Dir for `.env` Persistence
**Date**: 2026-05-25
**Context**: `update_env_file` wrote to a CWD-relative `.env`. This fails silently when the app
is installed via `pipx` (CWD is unpredictable) and caused age range / weight settings to not
persist across sessions.
**Decision**:
- All settings are written to `~/.config/netflix-narc/.env` via `platformdirs.user_config_dir("netflix-narc")`.
- `platformdirs` is already a transitive dependency (via Textual) — no new dep required.
- On first run after this change, an existing CWD `.env` is migrated to the config dir.
- `Settings.model_config["env_file"]` is updated to point at the config dir path.
**Rationale**: XDG-compliant, works with `pipx install`, survives CWD changes.

## 8. Onboarding → `OnboardingScreen` + `PreferencesScreen` (SetupScreen retired)
**Date**: 2026-05-25
**Context**: `SetupScreen` served double duty as first-run wizard and always-accessible settings.
It led with API key entry (optional feature), hid category weights entirely, and didn't reliably
persist settings.
**Decision**:
- `SetupScreen` is removed.
- `OnboardingScreen` (new, `onboarding.py`) — multi-step `ContentSwitcher` wizard, first-run only.
  Steps: Welcome → Age (required) → Weights (skippable) → API Keys (skippable) → Summary.
- `PreferencesScreen` (new, `preferences.py`) — always-accessible full settings panel, bound to `s`.
  Sections: Profile / Content Weights / API & Provider / Advanced.
- **`AdvancedScreen` is kept** (bound to `a`) for progressive disclosure. It surfaces `Load History
  File` and `Evaluate via API` for users who haven't discovered the hidden `c`/`e` key bindings.
  Only its description text is updated to remove the stale reference to "configured an API key in Setup".
**See**: `.agent/onboarding_overhaul.md` for full design, `.agent/onboarding_overhaul_plan.md` for implementation plan.


## 9. Weight Controls: Three-Button Toggle (1–3)
**Date**: 2026-05-25
**Context**: `CategoryWeights` fields are integers 1–3 with no UI exposure. The range was kept at
1–3 (Low / Med / High) for simplicity rather than expanding to 1–5.
**Decision**:
- `WeightRow` widget — three `Button` toggles (Low=1, Med=2, High=3). Active button uses `variant="primary"`.
- `↺` per-row reset button + "Reset All Weights" section button.
- `DEFAULT_WEIGHTS: ClassVar[dict[str, int]]` added to `CategoryWeights` as the canonical reference
  for the reset action.
- All seven `WEIGHTS__*` keys are written to `.env` on every save using pydantic-settings'
  existing `env_nested_delimiter = "__"` — no model changes needed.

## 10. Weight Impact Preview Panel (Live Before/After Score Preview)
**Date**: 2026-05-25
**Context**: Category weight adjustments are non-intuitive without concrete feedback. Users
have no way to know whether changing "Violence" from Med to High will affect 1 title or 20.
**Decision**:
- A `WeightImpactPreview` widget is shown beside the weight controls in both `PreferencesScreen`
  and `OnboardingScreen` Step 3.
- **Title selection**: filter `ManualMetadata` records with `completeness_score >= 70` and
  `ignored == False`, sort ascending by suitability score, then pick up to 6 titles using
  evenly-spaced index sampling (always includes the lowest and highest scoring title).
- **Reactivity**: `WeightRow` posts a `WeightRow.Changed` message on every button press; the
  preview panel recomputes all "After" scores in-memory without touching disk.
- **Baseline**: "Before" scores use the last-saved `CategoryWeights`. On `OnboardingScreen`
  (no prior save), `CategoryWeights()` defaults are used as the baseline.
- **Graceful hide**: if fewer than 2 eligible titles exist the panel is hidden entirely and
  replaced with a dim hint: "Complete more title dossiers (≥70%) to unlock the impact preview."
  This is the expected state on first run — no special-casing needed.
**See**: `.agent/weight_impact_preview.md` for full algorithm, rendering spec, and mockup.
