# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
