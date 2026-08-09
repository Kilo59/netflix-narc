# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0a6] - 2026-08-09

### Added
- **Spacebar Flag Shortcut**: Added `spacebar` keybinding to toggle "Flag for future follow-up" directly on selected titles in the main DataTable, Interrogation Room form, and Lineup screen.

## [0.1.0a5] - 2026-08-08

### Added
- **Distribution Smoke Test**: Added automated wheel build, venv installation, and isolated execution smoke test (`tests/test_distribution.py`) marked with `@pytest.mark.slow`.
- **SHA-256 Checksum Manifest**: Automated generation of `SHA256SUMS` in release pipeline and added verification instructions (`shasum -a 256 -c SHA256SUMS`) to `README.md`.

### Fixed
- **Wheel Package Data**: Added `[tool.setuptools.package-data]` to `pyproject.toml` to ensure `narc.tcss` is bundled into built `.whl` packages and PyApp executables, resolving `StylesheetError: unable to read CSS file`.
- **macOS Gatekeeper Quarantine**: Documented `xattr -d com.apple.quarantine netflix-narc` instructions in `README.md` and release notes to resolve browser download Gatekeeper process termination (`killed`).
- **macOS Ad-Hoc Code Signing**: Centralized ad-hoc code signing (`codesign --force --deep -s -`) in `tasks.py` (`build_binary`) for macOS targets with `shlex.quote` path escaping.

## [0.1.0a4] - 2026-08-01

### Added
- **PyPI & License Badges**: Added PyPI version, Python supported versions, and MIT License badges to `README.md`.

### Fixed
- **Windows Binary Builds**: Guarded `invoke` task `pty` option in `tasks.py` on Windows platforms where the `pty` standard library module is unsupported.

## [0.1.0a3] - 2026-08-01

### Added
- **Standalone Binaries via PyApp**: Support for building and distributing zero-dependency executables for macOS (ARM64 & Intel), Linux (x86_64), and Windows (x86_64) via `pyapp` and `invoke build-binary`.
- **CI Build & Caching**: Integrated `sccache` in GitHub Actions CI for fast incremental compilation of PyApp executable dependencies.

### Changed
- Bumped `idna` dependency from 3.11 to 3.15.
- Bumped `msgpack` dependency from 1.1.2 to 1.2.1.

## [0.1.0a2] - 2026-07-31

### Added
- **The Interrogation Suite**: Added `LineupScreen` (priority review queue) and `InterrogationRoomScreen` (manual metadata entry form for CSM category scores).
- **Onboarding & Preferences Overhaul**: Added `OnboardingScreen` multi-step setup wizard with live `WeightImpactPreview` and `PreferencesScreen` (`s` key).
- **Help Overlay & Visual Sub-bars**: Added `HelpScreen` (`h`/`?` key) and expandable suitability sub-bars in main DataTable.
- **Evidence Locker**: Local `aiosqlite` SQLite storage for manual dossier metadata with dossier completeness scoring.
- **BYOS Sync Compatibility**: Integrated `SyncEngine` for multi-device data & settings synchronization (LocalFolder, S3, WebDAV).

## [0.1.0a1] - 2026-04-01

### Added
- Initial project structure with `src` layout.
- Netflix viewing history CSV parser.
- Rating provider abstraction with OMDb and Common Sense Media (CSM) support.
- Weighted evaluation system for content flagging.
- Terminal User Interface (TUI) built with Textual.
- Persistent configuration via `.env` and `pydantic-settings`.
- HTTP caching using `hishel` to stay within API rate limits.
- Robust testing suite with `pytest` and `respx`.
- Linting and formatting with `Ruff`.
- Strict type-checking with `mypy`.
- **(Final Polish)**: Automated TUI mockup screenshot for README.
- **(Final Polish)**: Removed personal `NetflixViewingHistory.csv` from git tracking.
