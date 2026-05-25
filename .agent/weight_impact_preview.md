# Weight Impact Preview — Design

## Mockup

![Weight Impact Preview mockup](.agent/weight_impact_preview_mockup.png)

---

## Purpose

When adjusting category weights, it's not intuitive what a number change actually means for
real content. The **Weight Impact Preview** shows 2–6 titles from the user's own Evidence
Locker, rendered with their current ("before") suitability score alongside a live-recalculated
("after") score that updates as they move toggles — without saving anything.

---

## Placement

Side-by-side `Horizontal` layout with the weight controls in:
- `PreferencesScreen` — the **Content Weights** section
- `OnboardingScreen` — **Step 3** (Weights, skippable)

**Graceful hide**: if fewer than 2 eligible titles exist, the panel is hidden entirely and
replaced with a single dim hint line. This applies to all contexts including onboarding,
where a brand-new user will always see the hide state on first run.

---

## Title Selection Algorithm

### Step 1 — Filter

From `EvidenceLocker.get_all_records()`, keep records where:
- `completeness_score >= 70`
- `ignored == False`

### Step 2 — Score (baseline)

For each eligible record:
```python
baseline_score = calculate_suitability(
    record.to_normalized_metadata(),
    saved_settings,   # last-saved weights, NOT the current in-UI values
)
```

On **OnboardingScreen** (no saved settings yet), use `CategoryWeights()` defaults as the
baseline so the "Before" column reflects a meaningful reference point.

### Step 3 — Sort ascending

Sort records by `baseline_score` low → high. Worst-scoring titles appear first.

### Step 4 — Evenly-spaced sampling

```python
def _sample_indices(total: int, n: int) -> list[int]:
    if total <= n:
        return list(range(total))
    step = (total - 1) / (n - 1)
    return [round(i * step) for i in range(n)]

n = min(6, len(eligible))
indices = _sample_indices(len(sorted_records), n)
preview_titles = [sorted_records[i] for i in indices]
```

**Why evenly-spaced over top/bottom split?**
Avoids degenerate cases where titles cluster at one end of the scale — you'd get redundant
examples. Evenly-spaced indices guarantee index `0` (worst) and index `-1` (best) are always
included, with the rest spread across the middle regardless of score distribution.

**Example distributions:**

| Eligible titles | n | Indices selected |
|---|---|---|
| 2 | 2 | 0, 1 |
| 4 | 4 | 0, 1, 2, 3 |
| 10 | 6 | 0, 2, 4, 6, 8, 9 |
| 50 | 6 | 0, 10, 20, 30, 40, 49 |

### Step 5 — Minimum threshold

If `len(eligible) < 2`, **hide the preview panel** and show in its place:

```
Complete more title dossiers (≥70%) to unlock the impact preview.
```

---

## Rendering

For each selected title:

```
Breaking Bad
Before  ██░░░░░░░░ 2.3/10  →  After  █░░░░░░░░░ 1.1/10  ↓ −1.2
```

| Element | Detail |
|---------|--------|
| Title | Truncated to ~25 chars, bold white |
| Before bar | `get_suitability_bar(baseline_score, width=8)` |
| After bar | `get_suitability_bar(live_score, width=8)` — recalculated with in-UI weights |
| Delta | `↑ +N.N` green if positive, `↓ −N.N` red if negative, `—` if `abs(delta) < 0.05` |

Footer (dim grey): `N titles  •  ≥70% complete`

---

## Reactivity Model

1. `WeightRow` exposes a `reactive` `value: int` and posts a `WeightRow.Changed(value)` message
   on every button press.
2. `WeightImpactPreview` widget listens for `WeightRow.Changed` from its parent.
3. On each message it reconstructs a transient `CategoryWeights` from the current `WeightRow`
   states, re-runs `calculate_suitability` for each preview title, and refreshes the `Static`
   bars in-place.
4. **No disk writes.** The "After" score is purely in-memory until the user presses **Save**.

---

## Edge Cases

| Scenario | Behaviour |
|----------|-----------|
| `< 2` eligible titles | Panel hidden; "complete more dossiers" hint shown |
| All titles have identical scores | Sampling still valid; indices distributed across list |
| Weight change has no effect on a title | Delta shows `—` (no change) |
| Score exceeds bounds | `calculate_suitability` already clamps to `[0.0, 10.0]` |
| OnboardingScreen (no saved settings) | "Before" uses `CategoryWeights()` defaults as baseline |
