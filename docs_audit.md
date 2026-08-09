# Documentation Site Audit

**Audited**: [kilo59.github.io/netflix-narc](https://kilo59.github.io/netflix-narc/)
**Date**: 2026-08-09
**Scope**: All 6 docs site pages, source markdown, screenshots, and comparison against codebase + README

---

## Summary

The docs site covers the basic user journey (install → export CSV → onboard → use TUI) but has significant **feature coverage gaps** compared to what the codebase and README actually offer. Several major features are either undocumented or only briefly mentioned. Screenshots need updating to properly demonstrate the features they illustrate.

| Area | Status |
|------|--------|
| Site structure & navigation | ✅ Solid |
| Installation guide | ⚠️ Minor gaps vs README |
| Screenshot quality | ❌ Needs new captures |
| Feature coverage | ❌ Major gaps |
| Content depth | ⚠️ Thin in places |
| Cross-page consistency | ⚠️ Some drift from README |

---

## Zensical Docs Follow-up Phase — Cross-Reference

The [`.agent/zensical_docs_plan.md`](.agent/zensical_docs_plan.md) has an **incomplete Follow-up Phase** (Tasks 4.1–4.6) focused on media tooling and automated screenshot generation. Completing this phase would directly address several audit issues:

| Zensical Task | Status | Audit Issues Addressed |
|---------------|--------|------------------------|
| **4.1** Create `tapes/_common.tape` (VHS config) | ❌ Not started | Foundation for #10 (recordings) |
| **4.2** Add `screenshots` + `recordings` invoke tasks | ❌ Not started | Enables reproducible media generation for #1, #4, #10 |
| **4.3** Update CONTRIBUTING.md with media workflows | ❌ Not started | — (developer docs) |
| **4.4** Create VHS `.tape` scripts for demos | ❌ Not started | **Directly fixes #10** (empty `recordings/`). Would produce the onboarding demo, lineup/interrogation flow, and weight preview animations |
| **4.5** Create mock dataset fixtures for screenshots | ❌ Not started | **Directly fixes #1** — mock data with ≥2 completed dossiers would make the Weight Impact Preview render in screenshots |
| **4.6** Write `generate_tui_screenshots.py` | ❌ Not started | **Directly fixes #1, #4, #6** — programmatic screen navigation would capture Preferences (with preview), all Onboarding steps, Help Screen, Lineup card view, and Interrogation Room with populated data |

> [!IMPORTANT]
> Completing **Tasks 4.5 + 4.6** is the highest-leverage action. The current screenshot script skeleton in the plan already shows the right approach (Textual's `run_test()` pilot with `export_screenshot()`), but it needs mock fixtures to populate the Evidence Locker with enough data for the Weight Impact Preview to render. Without this, re-capturing screenshots manually will hit the same ≥2-dossier requirement that caused Issue #1 in the first place.

---

## Critical Issues

### 1. ❌ Preferences screenshot does NOT show the Weight Impact Preview
**Page**: [TUI Feature Walkthrough § Preferences](https://kilo59.github.io/netflix-narc/guides/tui-walkthrough/#3-preferences-live-weight-impact-preview-s)
**File**: [`docs/assets/images/preferences_screen.svg`](docs/assets/images/preferences_screen.svg)

> [!TIP]
> **Zensical follow-up overlap**: Tasks 4.5 (mock fixtures) + 4.6 (screenshot script) would fix this by populating the Evidence Locker with enough dossiers for the preview to render during automated capture.

The section title is **"Preferences & Live Weight Impact Preview"** and the text says *"the preview panel dynamically recalculates how many titles flip between Safe, Warning, and Flagged states"*, but the screenshot only shows the weight sliders — **the Weight Impact Preview panel is completely absent** from the SVG. The SVG contains zero text matching "WEIGHT IMPACT", "impact", "preview", or any `wip-` widget IDs.

This is likely because:
- The screenshot was taken without enough Evidence Locker data (the preview requires ≥2 titles with ≥70% dossier completeness to render)
- Or the terminal window was too narrow to show the side-by-side layout

**Fix**: Re-capture the Preferences screen with at least 2 completed dossiers so the `WeightImpactPreview` panel renders alongside the weight sliders. Ideally capture a wider terminal or provide two screenshots (one showing the sliders, one showing the preview in action with before/after bars and deltas).

### 2. ❌ Entire sections missing — Scoring Modes not documented anywhere
**Affected**: All docs pages (0 mentions of "Scoring Mode" across the entire site)

The codebase supports two distinct scoring modes that fundamentally change how suitability is calculated:
- **Quality Focus** (Option A): Gate factors (Age Suitability, Content Safety) act as penalty-only deductions
- **Balanced** (Option B): Gate factors contribute to a weighted average, capped at 7.0/10

These are configurable in both the **Onboarding Wizard** (Step 3) and the **Preferences screen** (`ScoringMode` select widget), yet the docs never mention them. The Troubleshooting FAQ even explains *"how does netflix-narc calculate severity scores?"* without mentioning scoring modes.

**Fix**: Add a section to the TUI Walkthrough (under Preferences) explaining the two scoring modes and when you'd choose one over the other. Also update the FAQ answer.

### 3. ❌ BYOS Storage & Sync feature completely undocumented
**Affected**: No dedicated guide; only brief passing mentions in `tui-walkthrough.md` and `index.md`

The README dedicates an entire section to **Bring-Your-Own-Storage (BYOS)** with detailed configuration for:
- Local Folder / iCloud Drive
- S3-compatible object storage (Cloudflare R2, AWS S3, MinIO, Wasabi)
- WebDAV / Nextcloud / ownCloud

The docs site has **zero** coverage of this feature. The `SetupScreen` and `AdvancedScreen` in `main.py` include full sync configuration UI, test connection functionality, and environment variable support — none of which is documented.

**Fix**: Create a new docs page `guides/storage-and-sync.md` covering backend selection, credential setup, the Test Connection button, and `.env` configuration for each backend type.

---

## Important Issues

### 4. ⚠️ Onboarding guide only shows 1 screenshot — missing Steps 2 and 3
**Page**: [Onboarding & Setup](https://kilo59.github.io/netflix-narc/guides/onboarding-and-setup/)
**File**: [`docs/guides/onboarding-and-setup.md`](docs/guides/onboarding-and-setup.md)

> [!TIP]
> **Zensical follow-up overlap**: Task 4.6 (`generate_tui_screenshots.py`) would automate capturing each onboarding step by programmatically pressing Next through the wizard.

The onboarding wizard has multiple steps (age range → API keys → weight configuration → scoring mode), but the guide only shows a single screenshot of what appears to be Step 1. Steps for weight configuration and scoring mode selection during onboarding are not visually documented.

**Fix**: Add screenshots for each onboarding step, especially the weight tuning step where the Weight Impact Preview first appears.

### 5. ⚠️ Interrogation Room docs are too thin — missing key features
**Page**: [TUI Feature Walkthrough § Interrogation Room](https://kilo59.github.io/netflix-narc/guides/tui-walkthrough/#2-the-interrogation-room-i)

The docs list 3 bullet points but the actual `InterrogationRoomScreen` has significantly more functionality:
- **Real-time suitability dashboard** with live overall + sub-bar scores that update as you type (not mentioned)
- **Sub-suitability breakdown bars** (Base Quality, Age Suitability, Educational Suitability, Positive Content, Content Safety) — not documented
- **CSM category score inputs** (0-5 scale for Violence, Language, Sexual Content, etc.) — only vaguely referenced
- **Cover image paste from clipboard** (macOS) and URL download — not mentioned
- **Web search shortcut** (F2 opens CSM search in browser) — not mentioned
- **Detailed score breakdown tooltip** on hover over the suitability dashboard — not mentioned
- **Flag for follow-up checkbox** — not mentioned
- **Quality Rating input** (1-5 stars) — not mentioned

**Fix**: Expand the Interrogation Room section with a more detailed feature list and add a screenshot that shows the form with data filled in and the suitability bars active.

### 6. ⚠️ Help Screen not documented
**File**: [`src/netflix_narc/help_screen.py`](src/netflix_narc/help_screen.py)

> [!TIP]
> **Zensical follow-up overlap**: Task 4.6 (`generate_tui_screenshots.py`) can capture this screen automatically by navigating to it via `pilot.press("?")` during the screenshot run.

The app has a dedicated `HelpScreen` accessible via `?` or `h` that explains the app philosophy, how scoring works, and lists keybindings. The docs site never mentions this screen exists. The keybindings table in the TUI Walkthrough lists `?` → "Help Modal" but doesn't describe what it contains.

**Fix**: Add a brief note (or screenshot) showing the Help Screen content, or at minimum describe what information it provides.

### 7. ⚠️ Lineup Screen documentation is misleading
**Page**: [TUI Feature Walkthrough § Lineup Screen](https://kilo59.github.io/netflix-narc/guides/tui-walkthrough/#1-the-lineup-screen-l)

The docs describe it as *"your primary inspection dashboard"* with severity indicators and quick filtering, but the actual `LineupScreen` is a **sequential card-based review queue**, not a dashboard. It shows:
- One title at a time (card view with counter "Title N of M")
- Title, view count, first/last watched dates
- **Dossier completeness progress bar** (not mentioned in docs)
- Three actions: Interrogate [I], Ignore [X], Skip [S]

The docs incorrectly describe filtering and severity indicators that don't exist on the Lineup Screen — those features are on the **main DataTable** (the app's home screen, which isn't separately documented).

**Fix**: Rewrite the Lineup section to accurately describe the sequential card-based review flow, and consider adding a section for the main DataTable view (which has the expand/collapse, sub-bars, and severity indicators the docs currently misattribute to the Lineup).

---

## Minor Issues

### 8. Installation guide lags behind README
**File**: [`docs/getting-started/installation.md`](docs/getting-started/installation.md)

| Detail | README | Docs Site |
|--------|--------|-----------|
| Binary naming convention | Architecture-specific names (`netflix-narc-aarch64-apple-darwin.tar.gz`) | Generic names (`netflix-narc-macos`) |
| Archive extraction | `tar -xzf` instructions | Not mentioned (implies raw binary download) |
| `pipx` install option | Listed | Not mentioned |
| Source install from GitHub | `uv tool install git+https://github.com/...` | Not mentioned |
| SHA256 verification | Full instructions | Not mentioned |
| Development setup | Listed | Not mentioned |

**Fix**: Update the installation docs to match the README's more detailed and current binary names, add archive extraction steps, and include SHA256 verification instructions.

### 9. Exporting CSV page uses ASCII art instead of actual screenshot
**File**: [`docs/getting-started/exporting-netflix-csv.md`](docs/getting-started/exporting-netflix-csv.md)

The page uses a text-based ASCII box diagram to represent the Netflix Viewing Activity page. While functional, an actual screenshot of the Netflix page (or a stylized mockup) would be much more helpful for users trying to find the "Download all" button.

**Fix**: Add a screenshot or annotated mockup of the Netflix Viewing Activity page showing where the "Download all" button is located.

### 10. Missing `recordings/` content
**Directory**: [`docs/assets/recordings/`](docs/assets/recordings/) — empty

> [!TIP]
> **Zensical follow-up overlap**: Tasks 4.1 (VHS common config) + 4.4 (VHS `.tape` scripts) are specifically designed to fill this directory. The plan already specifies `tapes/onboarding_demo.tape` and `tapes/lineup_filtering.tape` as initial recordings.

The docs have a `recordings/` directory set up but it contains no files. Animated recordings (`.gif` or `.webm`) of key workflows would significantly improve the docs:
- The Onboarding wizard flow
- Adjusting weights and seeing the live preview react
- The Lineup → Interrogation Room workflow
- Expanding rows to see sub-suitability bars

**Fix**: Record short demos of key workflows using a tool like `vhs` or `asciinema` and add them to relevant sections.

### 11. Keybindings table is incomplete
**Page**: [TUI Feature Walkthrough § Global Navigation](https://kilo59.github.io/netflix-narc/guides/tui-walkthrough/#global-navigation-keybindings)

Missing from the documented keybindings:

| Key | Action | Notes |
|-----|--------|-------|
| `h` | Help Screen | Listed as `?` only |
| `a` | Advanced Options | Not listed |
| `c` | Load History File | Hidden power-user binding |
| `e` | Evaluate Titles | Hidden power-user binding |
| `f10` | Quit | Not listed |
| `ctrl+c` | Quit | Not listed |
| `F2` (in Interrogation Room) | Search Web | Screen-specific binding |
| `x` (in Lineup) | Ignore title | Screen-specific binding |

**Fix**: Add the missing keybindings. Consider splitting into "Global" and "Screen-specific" tables.

### 12. Sub-suitability bars not documented
The main DataTable and Interrogation Room both display **5 sub-suitability breakdown bars** when a title is expanded:
- Base Quality
- Age Suitability
- Educational Suitability
- Positive Content
- Content Safety

These are defined in [`evaluator.py`'s `SUB_BAR_DEFINITIONS`](src/netflix_narc/evaluator.py) and are a key part of the evaluation UX, but they're not documented anywhere.

**Fix**: Add a section explaining the sub-bar breakdown, what each bar measures, and how they relate to the overall suitability score.

### 13. Advanced Options screen not documented
The `AdvancedScreen` (bound to `a`) provides progressive disclosure for:
- **Load History File [C]**: Reload Netflix viewing history from a file
- **Evaluate Titles via API [E]**: Fetch ratings from the configured provider

This screen is not mentioned in the docs at all.

**Fix**: Add a brief section to the TUI Walkthrough describing the Advanced Options modal.

### 14. Docs index feature list mentions "Quick Filtering" which doesn't exist as described
**File**: [`docs/index.md`](docs/index.md)

The homepage describes *"Toggle view between all titles, flagged titles only, or unrated items"* — this filter toggle doesn't appear to exist in the current codebase. The main DataTable shows all titles; there's no filter toggle UI.

**Fix**: Remove or update this claim to match actual functionality.

### 15. `docs/index.md` description of Weight Impact Preview is inaccurate
The docs describe the preview as showing *"how many titles in your viewing history flip between Safe, Warning, and Flagged states"*. The actual preview shows individual title suitability score bars (before/after) with delta values — it doesn't count or categorize titles into Safe/Warning/Flagged buckets.

**Fix**: Update the description to accurately reflect the before/after suitability bar comparison.

---

## Structural Recommendations

### 16. Missing page: Main DataTable view
The app's primary home screen (the `DataTable` with expandable rows, suitability bars, flags, and sub-bar breakdowns) has **no dedicated documentation**. The docs jump from Onboarding to the Lineup/Interrogation Room, but the main table is what users see first after setup.

**Fix**: Add a section or page documenting the main table view, including row expansion, severity colors, and the sorting/priority algorithm.

### 17. Missing page: Evidence Locker concepts
The Evidence Locker (async SQLite database for manual data) is referenced across multiple pages but never explained as a concept. Users should understand:
- What data it stores
- How completeness scores work (0-100%)
- How manual entries interact with API data (merge behavior)
- Where the database file lives

**Fix**: Add a "Concepts" section or page explaining the Evidence Locker.

### 18. Missing page: Storage & Sync (BYOS)
As noted in Issue #3, the entire BYOS feature needs its own guide.

### 19. Nav structure improvement
The current nav has 3 top-level groups: Overview, Getting Started, User Guides. Consider adding:
- **Reference** section for: Keybindings (comprehensive), Scoring algorithm, Provider comparison
- **Concepts** section for: Evidence Locker, Scoring modes, Weight system

---

## Screenshot Inventory

| Screenshot | File | Shows | Issues |
|-----------|------|-------|--------|
| Lineup Screen | `lineup_screen.svg` | Main DataTable (not Lineup) | Potentially mislabeled — review if it actually shows the card-based Lineup or the DataTable |
| Interrogation Room | `interrogation_screen.svg` | Interrogation form | Verify it shows populated data and suitability bars |
| Onboarding Screen | `onboarding_screen.svg` | Step 1 of onboarding | Only 1 step shown; need all steps |
| Preferences Screen | `preferences_screen.svg` | Weight sliders only | **Missing**: Weight Impact Preview panel |

### Screenshots needed (new)

> [!NOTE]
> All items below would be produced automatically by completing the **zensical follow-up phase** (Tasks 4.5 + 4.6 in [`.agent/zensical_docs_plan.md`](.agent/zensical_docs_plan.md)). The `generate_tui_screenshots.py` script using Textual Pilot can navigate to each screen and export SVGs programmatically.

- [ ] Preferences with Weight Impact Preview panel visible
- [ ] Onboarding Steps 2, 3 (API keys, weight tuning with scoring mode)
- [ ] Help Screen
- [ ] Lineup Screen (the actual card-based queue view)
- [ ] Advanced Options modal
- [ ] Main DataTable with expanded row showing sub-bars
- [ ] Interrogation Room with filled data and live suitability bars

---

## Remediation Plan & Prioritized Execution Order

Below is the structured, sequential task breakdown to resolve all audit findings and complete the Zensical documentation site.

### 📦 Phase 1: Automated Media Infrastructure & Fixtures (High Leverage)
*Goal: Build the programmatic screenshot script and test fixtures so that all missing/broken screenshots (e.g. Weight Impact Preview) can be generated automatically with populated data.*

- [x] **Task 1.1 — Mock Dataset Fixtures (`zensical_docs_plan.md` Task 4.5)**
  - Create mock `ManualMetadata` records with completeness scores $\ge 70\%$ in `scripts/generate_tui_screenshots.py` so the `WeightImpactPreview` widget actually renders when the Preferences and Onboarding screens are captured.
- [x] **Task 1.2 — Automated TUI Screenshot Script (`zensical_docs_plan.md` Task 4.6)**
  - Implement `scripts/generate_tui_screenshots.py` using Textual's `run_test()` pilot to programmatically navigate and save native SVG screenshots for:
    - Preferences Screen (with `WeightImpactPreview` panel visible — **fixes Audit #1**)
    - Onboarding Steps 1, 2, 3 (**fixes Audit #4**)
    - Help Screen (`?`) (**fixes Audit #6**)
    - Lineup card view (**fixes Audit #7**)
    - Main DataTable with expanded row & sub-bars (**fixes Audit #12**)
    - Interrogation Room with populated scores & live suitability bars (**fixes Audit #5**)
    - Advanced Options modal (**fixes Audit #13**)
- [x] **Task 1.3 — Invoke Tasks & Contributing Docs (`zensical_docs_plan.md` Tasks 4.2 & 4.3)**
  - Add `inv screenshots` and `inv recordings` tasks to `tasks.py` and document them in `CONTRIBUTING.md`.

### ✍️ Phase 2: Missing Documentation Content & Accuracy Fixes
*Goal: Fix inaccurate descriptions, document missing features (Scoring Modes, BYOS Sync, Sub-bars), and create missing guide pages.*

- [x] **Task 2.1 — Storage & Sync (BYOS) Guide (Audit #3 & #18)**
  - Create `docs/guides/storage-and-sync.md` covering Local Folder/iCloud, S3/Cloudflare R2, and WebDAV/Nextcloud configurations, test connection button, and `.env` setup. Update `zensical.toml` navigation.
- [x] **Task 2.2 — Scoring Modes & Algorithm Section (Audit #2)**
  - Add a dedicated section to `tui-walkthrough.md` (under Preferences) explaining **Quality Focus** vs **Balanced** scoring modes. Update the FAQ response in `troubleshooting-faq.md`.
- [x] **Task 2.3 — Correct Lineup vs Main DataTable Descriptions (Audit #7 & #16)**
  - Rewrite `tui-walkthrough.md` § 1 to accurately describe the sequential card review flow (Lineup). Add a new section for the **Main Inspection Table** (expandable rows, severity colors, view counts).
- [x] **Task 2.4 — Expand Interrogation Room Details (Audit #5)**
  - Update `tui-walkthrough.md` § 2 to cover real-time suitability dashboard, sub-suitability bars, macOS clipboard image pasting, F2 web search, and follow-up flags.
- [x] **Task 2.5 — Document Sub-bars, Help Screen & Advanced Options (Audit #6, #12, #13)**
  - Add sections in `tui-walkthrough.md` for the 5 sub-suitability breakdown bars, the Help Screen (`h`/`?`), and the Advanced Options modal (`a`).
- [x] **Task 2.6 — Comprehensive Keybindings Table (Audit #11)**
  - Expand the keybindings reference table in `tui-walkthrough.md` to include missing keys (`h`, `a`, `c`, `e`, `f10`, `F2`, `x`).
- [x] **Task 2.7 — Homepage & Installation Alignment (Audit #8, #14, #15)**
  - Fix `docs/index.md` (remove bogus "Quick Filtering" toggle claim; fix Weight Preview description).
  - Sync `docs/getting-started/installation.md` with `README.md` (architecture-specific binary tarballs, `xattr` quarantine fix, `pipx`, SHA256 checksum verification).

### 📸 Phase 3: Screenshot Re-capture & Visual Verification
*Goal: Run the automated screenshot generator and embed updated SVGs into the docs.*

- [x] **Task 3.1 — Re-generate SVG Assets**
  - Run `uv run inv screenshots` to produce all updated SVG captures into `docs/assets/images/`.
- [x] **Task 3.2 — Update Markdown Image Embeds**
  - Update `tui-walkthrough.md`, `onboarding-and-setup.md`, and `index.md` to reference the newly captured screenshots (including Onboarding steps, Help Screen, DataTable sub-bars, and Preferences with preview).

### 🎥 Phase 4: Animated CLI Recordings & Final Verification
*Goal: Create animated VHS terminal recordings and verify the built Zensical site.*

- [x] **Task 4.1 — VHS Config & Tape Scripts (`zensical_docs_plan.md` Tasks 4.1 & 4.4 / Audit #10)**
  - Create `tapes/_common.tape`, `tapes/onboarding_demo.tape`, and `tapes/lineup_filtering.tape`.
  - Run `uv run inv recordings` to render `.gif` animations into `docs/assets/recordings/`.
- [x] **Task 4.2 — Embed Recordings in Docs**
  - Embed the generated GIFs in `onboarding-and-setup.md` and `tui-walkthrough.md`.
- [x] **Task 4.3 — End-to-End Build & Validation**
  - Run `uv run --group docs zensical build` to ensure 0 build errors, clean internal links, and a fully rendered `site/` output.
