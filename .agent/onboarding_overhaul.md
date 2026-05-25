# Onboarding & Settings Overhaul — Requirements & Design

> **Decisions locked in:**
> 1. `.env` moves to `~/.config/netflix-narc/` (XDG-compliant, works with `pipx install`)
> 2. Multi-step wizard uses `ContentSwitcher` (enforced step ordering)
> 3. Weight range: **1–5** (V.Low / Low / Medium / High / V.High) — *[SUPERSEDED by ADR 11's 1-5 expansion]*

## Problem Statement

The current `SetupScreen` (bound to `s`) serves double duty as both the mandatory first-run
onboarding flow and an always-available settings panel. It has several structural problems:

| # | Problem | Root Cause |
|---|---------|-----------|
| 1 | Age range is not persisted across sessions | `update_env_file` in `persistence.py` only writes `CHILD_AGE_RANGE` when called; the `_save_settings` codepath in `SetupScreen` does call it, but the key is missing from the initial `.env` in many environments |
| 2 | No obvious way to revisit settings once onboarding is dismissed | The `s` keybinding reaches `SetupScreen`, but this is not surfaced clearly in the UI; casual users won't discover it |
| 3 | API key entry dominates the flow | The setup form opens immediately asking for a Provider + API Key before anything else — this is a high-friction first impression for a feature (auto-rating) that is entirely optional |
| 4 | Category weights are invisible and non-configurable from the UI | `CategoryWeights` exists in `settings.py` and is used by `evaluator.py`, but users can only change them by editing `.env` manually |
| 5 | Settings don't fully persist; screen reappears unnecessarily | `needs_onboarding = self.settings.child_age_range is None` — only `child_age_range` is checked, but even when set it can still be `None` after restart if persistence fails |

---

## Goals

1. **Age range always persists** — written to `~/.config/netflix-narc/.env` and re-read on every startup.
2. **Settings are easily revisitable** — a dedicated "Preferences" screen accessible at any time without feeling like a reset.
3. **API keys are optional and de-emphasized** — moved to a separate, skippable step so the main onboarding doesn't lead with them.
4. **Category weights are exposed** — users can see the current weight per category, adjust them, and reset to factory defaults.
5. **One-time onboarding** — the full onboarding flow only appears when truly required settings are missing. Subsequent launches skip it.

---

## Decisions

| # | Question | Decision |
|---|----------|----------|
| 1 | Where to store `.env`? | `~/.config/netflix-narc/.env` via `platformdirs.user_config_dir()`. Already a transitive dep via Textual. |
| 2 | Multi-step wizard navigation? | `ContentSwitcher` — enforces step order, prevents jumping to API keys before age is set. |
| 3 | Weight range? | `1–5` (V.Low / Low / Medium / High / V.High) — *[SUPERSEDED by ADR 11]* |

---

## Proposed Architecture

### Screens

#### 1. `OnboardingScreen` (replaces first-run `SetupScreen` popup) — NEW

A multi-step wizard shown **only** when `child_age_range is None`. Lightweight, focused on the
minimum viable configuration.

**Steps (via `ContentSwitcher`):**

| Step ID | Title | Required? | Content |
|---------|-------|-----------|---------|
| `step-welcome` | Welcome | — | App name, tagline, "Let's get started →" button |
| `step-age` | Child's Age | ✅ | Age / range `Input`; validates before Next is enabled |
| `step-weights` | Content Weights | optional | Weight rows for all 7 categories; "Reset All" button; "Skip →" action |
| `step-api` | API Provider | optional | Provider `Select` + masked key `Input`; "Skip →" action |
| `step-summary` | Ready | — | Recap of chosen settings; "Start Narcing" primary button |

Navigation: `Next →` / `← Back` buttons + step indicator (dots). Escape dismisses → app exits (first-run only).

#### 2. `PreferencesScreen` (replaces `SetupScreen` for the `s` keybinding) — REFACTOR

A full settings panel, always accessible. Does **not** exit the app on cancel/close.

| Section | Fields |
|---------|--------|
| **Profile** | Child age range |
| **Weights** | All `CategoryWeights` fields with ± toggles + "Reset to Defaults" |
| **API / Provider** | Provider dropdown + API key input |
| **Advanced** | `max_records`, `min_quality_rating`, `max_age_rating`, `merge_manual_data` |

---

### Persistence Changes

#### `persistence.py`

Extend `_get_env_values` to write all seven `WEIGHTS__*` env vars using pydantic-settings'
existing `env_nested_delimiter = "__"`:

```
WEIGHTS__EDUCATIONAL_VALUE=1
WEIGHTS__POSITIVE_MESSAGES=1
WEIGHTS__POSITIVE_ROLE_MODELS=1
WEIGHTS__VIOLENCE=3
WEIGHTS__SEXY_STUFF=3
WEIGHTS__LANGUAGE=2
WEIGHTS__DRINKING_DRUGS=3
```

Default `.env` path becomes `get_config_dir() / ".env"`.
Migrate an existing CWD `.env` to config dir on first run if found.

#### `settings.py`

Add `get_config_dir()` helper using `platformdirs.user_config_dir("netflix-narc")`.
Update `Settings.model_config` to point `env_file` at the config dir.
Add `DEFAULT_WEIGHTS: ClassVar[dict[str, int]]` to `CategoryWeights`.

---

### UI Widget — Weight Controls

Each weight row in both `OnboardingScreen` and `PreferencesScreen`:

```
Violence & Scariness    [Low]  [■ Med]  [High]   ↺
```

- Five `Button` toggles: V.Low (1) / Low (2) / Med (3) / High (4) / V.High (5). Active one renders as `variant="primary"`. — *[UPDATED by ADR 11]*
- `↺` resets that row to its default value.
- "Reset All Weights" button at the bottom of the section.
- Implemented as a `WeightRow(Widget)` composite with a `reactive` int value.

---

### Weight Impact Preview Panel

See **[`.agent/weight_impact_preview.md`](.agent/weight_impact_preview.md)** for full spec and mockup.

Shown **beside** the weight controls (side-by-side `Horizontal` layout) in both
`PreferencesScreen` (Weights section) and `OnboardingScreen` (Step 3 — Weights).

Updates **reactively** every time any `WeightRow` value changes — no save required.

**Graceful hide**: if fewer than 2 `ManualMetadata` records have `completeness_score >= 70`,
the panel is hidden and replaced with a dim hint line. This applies on `OnboardingScreen` too
— first-run users will always see the hide state, which is expected and fine.

**Title selection summary** (full algorithm in weight_impact_preview.md):
1. Filter: `completeness_score >= 70`, `ignored == False`
2. Score each with `calculate_suitability()` using the **saved** weights as baseline (onboarding falls back to `CategoryWeights()` defaults)
3. Sort ascending by score
4. Evenly-spaced index sampling — picks `min(6, n)` titles always including the lowest and highest scoring

### Return Types

`OnboardingScreen` returns:
```python
class OnboardingResult(NamedTuple):
    child_age_range: tuple[int, int]
    weights: CategoryWeights
    provider: RatingProviderType | None   # None = skipped
    api_key: SecretStr | None             # None = skipped
```

`PreferencesScreen` saves directly via `update_env_file` and updates `app.settings` in-memory.

---

### `main.py` Changes

- Remove `SetupConfig` NamedTuple and `SetupScreen` class.
- **Keep `AdvancedScreen`** (bound to `a`) — it exists for progressive disclosure. Users who want
  to load a new CSV or trigger an API evaluation can discover these actions here without needing
  to know the hidden `c`/`e` key bindings. Update its description text only (remove the stale
  reference to "configured an API key in Setup").
- Push `OnboardingScreen` on first run; push `PreferencesScreen` for `s` key.
- Pass `get_config_dir() / ".env"` everywhere `update_env_file` is called.

---

## Files Changed

| File | Change |
|------|--------|
| `src/netflix_narc/settings.py` | Add `get_config_dir()`, update `env_file` path, add `DEFAULT_WEIGHTS` |
| `src/netflix_narc/persistence.py` | Write all `WEIGHTS__*` fields; use config dir path |
| `src/netflix_narc/main.py` | Remove `SetupScreen`/`SetupConfig`; wire `OnboardingScreen` + `PreferencesScreen`; update `AdvancedScreen` description text |
| `src/netflix_narc/onboarding.py` | **NEW** — multi-step wizard |
| `src/netflix_narc/preferences.py` | **NEW** — always-accessible settings panel |
| `src/netflix_narc/narc.tcss` | New styles for wizard, step indicator, weight rows, preferences |
| `src/netflix_narc/help_screen.py` | Update key binding descriptions (`s` → Preferences) |
| `tests/test_persistence.py` | **NEW** — round-trip tests for weight + config-dir persistence |
| `tests/test_onboarding.py` | **NEW** — structural tests for onboarding wizard flow |
