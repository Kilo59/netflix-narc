# Implementation Plan — Onboarding & Settings Overhaul

See design doc: [`.agent/onboarding_overhaul.md`](.agent/onboarding_overhaul.md)

## Goal

Replace the current single-form `SetupScreen` with:
1. A **multi-step `OnboardingScreen`** (first-run only, `ContentSwitcher`-based)
2. A **`PreferencesScreen`** (always accessible via `s`, never exits on cancel)

Fix all five problems: age range persistence, revisitability, API key de-emphasis,
exposed weight controls, and reliable one-time onboarding.

---

## Proposed Changes

### Settings & Config Dir

#### [MODIFY] `src/netflix_narc/settings.py`

- Add `get_config_dir() -> pathlib.Path` helper using `platformdirs.user_config_dir("netflix-narc")`.
- Update `Settings.model_config` to point `env_file` at `get_config_dir() / ".env"`.
- Add `DEFAULT_WEIGHTS: ClassVar[dict[str, int]]` to `CategoryWeights` for "Reset to Defaults".

```python
def get_config_dir() -> pathlib.Path:
    import platformdirs
    d = pathlib.Path(platformdirs.user_config_dir("netflix-narc"))
    d.mkdir(parents=True, exist_ok=True)
    return d
```

---

### Persistence

#### [MODIFY] `src/netflix_narc/persistence.py`

- Update `_get_env_values` to also write all seven `WEIGHTS__*` env vars.
- Update `update_env_file` signature: accept `weights: CategoryWeights | None = None`.
- Default `env_path` becomes `get_config_dir() / ".env"`.
- On first run, migrate an existing CWD `.env` to config dir if found.

---

### New Screens

#### [NEW] `src/netflix_narc/onboarding.py`

`OnboardingScreen(Screen[OnboardingResult | None])` — first-run only.

**Return type:**
```python
class OnboardingResult(NamedTuple):
    child_age_range: tuple[int, int]
    weights: CategoryWeights
    provider: RatingProviderType | None   # None = skipped
    api_key: SecretStr | None             # None = skipped
```

**Steps (ContentSwitcher):**

| Step ID | Required? | Content |
|---------|-----------|---------|
| `step-welcome` | — | App name, tagline, "Let's get started →" |
| `step-age` | ✅ | Age/range Input; Next disabled until valid |
| `step-weights` | optional | 7 × `WeightRow` widget; Reset All; Skip → |
| `step-api` | optional | Provider Select + masked Input; Skip → |
| `step-summary` | — | Recap; "Start Narcing" primary button |

Step indicator: `Horizontal` of dot `Static` widgets updated reactively.

`WeightRow(Widget)` — three-button toggle (Low=1, Med=2, High=3) + ↺ reset.

---

#### [NEW] `src/netflix_narc/preferences.py`

`PreferencesScreen(Screen[None])` — always accessible, close without saving via Escape.

Sections (vertical scroll):
- **Profile** — child age range
- **Content Weights** — `WeightRow` × 7 + "Reset All Weights"
- **API / Provider** — provider Select + masked key Input
- **Advanced** — `max_records`, `min_quality_rating`, `max_age_rating`, `merge_manual_data` Switch

Footer: `Save` (write `.env`, update `app.settings`, notify) + `Close` (Escape/q).

---

### Main App

#### [MODIFY] `src/netflix_narc/main.py`

- **Remove** `SetupConfig`, `SetupScreen`.
- **Keep `AdvancedScreen`** (bound to `a`) — progressive disclosure for `Load CSV` and `Evaluate
  via API`. Update its static description text to remove the stale "configured an API key in
  Setup" wording.
- Push `OnboardingScreen` (not `SetupScreen`) for first-run.
- `action_settings` → push `PreferencesScreen`.
- `handle_startup_onboarding_complete` accepts `OnboardingResult | None`.
- Pass `get_config_dir() / ".env"` to all `update_env_file` calls.

---

### CSS

#### [MODIFY] `src/netflix_narc/narc.tcss`

New selectors:
- `#onboarding-container`, `#step-indicator`, `.step-dot`, `.step-dot-active`
- `.weight-row`, `.weight-label`, `.weight-btn`, `.weight-reset-btn`
- `#preferences-container`, `#preferences-card`, `.pref-section-header`

---

### Help Screen

#### [MODIFY] `src/netflix_narc/help_screen.py`

- Update key binding table: `S` → "Preferences" (was "Setup").
- Remove reference to `A` → Advanced (screen removed).

---

### Tests

#### [NEW] `tests/test_persistence.py`

- `test_update_env_file_writes_weights` — write weights to `tmp_path`-based `.env`, re-read with `Settings`, assert all 7 `WEIGHTS__*` round-trip correctly.
- `test_get_env_values_includes_all_weight_keys` — assert all 7 keys present in output dict.
- `test_update_env_file_migration` — existing CWD `.env` is migrated to config dir path.

#### [NEW] `tests/test_onboarding.py`

- `test_onboarding_result_defaults` — skipping Step 3 yields default `CategoryWeights`.
- `test_weight_row_clamp` — `WeightRow` value never goes below 1 or above 3.

---

## Verification Plan

### Automated Tests

```bash
uv run ruff check . --fix
uv run ruff format .
uv run mypy .
uv run pytest -vv
```

### Manual Smoke Tests

1. **First run** (delete `~/.config/netflix-narc/.env`) — wizard appears, step indicator
   advances, age required before Next, weights/API steps skippable, summary correct, app starts.
2. **Subsequent run** — wizard does NOT appear. App loads with persisted settings.
3. **`s` key** — `PreferencesScreen` opens, shows current values, Save persists changes.
4. **Reset to defaults** — "Reset All Weights" restores `CategoryWeights.DEFAULT_WEIGHTS`.
5. **Config dir** — `cat ~/.config/netflix-narc/.env` shows all `WEIGHTS__*` and `CHILD_AGE_RANGE`.
