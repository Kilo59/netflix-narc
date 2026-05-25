"""Persistence utilities for Netflix Narc."""

from __future__ import annotations

import pathlib
from typing import TYPE_CHECKING

from netflix_narc.parser import parse_netflix_history
from netflix_narc.settings import RatingProviderType, ScoringMode, get_config_dir

if TYPE_CHECKING:
    from pydantic import SecretStr

    from netflix_narc.parser import ViewingRecord
    from netflix_narc.settings import CategoryWeights


def _parse_env_line(raw_line: str, new_values: dict[str, str], seen_keys: set[str]) -> str | None:
    """Parse a single .env line and return the updated version, or None if skipped."""
    line = raw_line.strip()
    if not line or line.startswith("#"):
        return line

    if "=" in line:
        k, _ = line.split("=", 1)
        if k in new_values:
            seen_keys.add(k)
            return f"{k}={new_values[k]}"
        return line
    return line


def _get_env_values(
    provider: RatingProviderType,
    api_key: SecretStr,
    child_age_range: tuple[int, int] | None,
    weights: CategoryWeights | None = None,
    scoring_mode: ScoringMode | None = None,
) -> dict[str, str]:
    """Build the dictionary of configuration values to persist in .env."""
    vals = {
        "ACTIVE_RATING_PROVIDER": str(provider),
    }
    if provider == RatingProviderType.CSM:
        vals["CSM_API_KEY"] = api_key.get_secret_value()
    elif provider == RatingProviderType.OMDB:
        vals["OMDB_API_KEY"] = api_key.get_secret_value()

    if child_age_range is not None:
        vals["CHILD_AGE_RANGE"] = f"{child_age_range[0]},{child_age_range[1]}"

    if scoring_mode is not None:
        vals["SCORING_MODE"] = str(scoring_mode)

    if weights is not None:
        vals["WEIGHTS__BASE_QUALITY"] = str(weights.base_quality)
        vals["WEIGHTS__AGE_SUITABILITY"] = str(weights.age_suitability)
        vals["WEIGHTS__EDUCATIONAL_VALUE"] = str(weights.educational_value)
        vals["WEIGHTS__POSITIVE_MESSAGES"] = str(weights.positive_messages)
        vals["WEIGHTS__POSITIVE_ROLE_MODELS"] = str(weights.positive_role_models)
        vals["WEIGHTS__VIOLENCE"] = str(weights.violence)
        vals["WEIGHTS__SEXY_STUFF"] = str(weights.sexy_stuff)
        vals["WEIGHTS__LANGUAGE"] = str(weights.language)
        vals["WEIGHTS__DRINKING_DRUGS"] = str(weights.drinking_drugs)

    return vals


def update_env_file(
    provider: RatingProviderType,
    api_key: SecretStr,
    env_path: pathlib.Path | None = None,
    child_age_range: tuple[int, int] | None = None,
    weights: CategoryWeights | None = None,
    scoring_mode: ScoringMode | None = None,
) -> None:
    """Update the .env file with new provider settings, deduplicating keys.

    Defaults to the XDG config dir (~/.config/netflix-narc/.env).
    If an existing CWD .env is found on first run it is migrated to the config dir.
    """
    resolved_path = env_path if env_path is not None else get_config_dir() / ".env"

    # One-time migration: if a CWD .env exists and config dir file doesn't yet, migrate it.
    cwd_env = pathlib.Path(".env")
    if cwd_env.exists() and not resolved_path.exists() and resolved_path != cwd_env:
        resolved_path.write_text(cwd_env.read_text(encoding="utf-8"), encoding="utf-8")

    env_lines: list[str] = []
    if resolved_path.exists():
        env_lines = resolved_path.read_text(encoding="utf-8").splitlines()

    new_values = _get_env_values(provider, api_key, child_age_range, weights, scoring_mode)

    # Process existing lines, updating matches
    updated_lines: list[str] = []
    seen_keys: set[str] = set()
    for raw_line in env_lines:
        updated_line = _parse_env_line(raw_line, new_values, seen_keys)
        if updated_line is not None:
            updated_lines.append(updated_line)

    # Add new keys that weren't in the file
    for k, v in new_values.items():
        if k not in seen_keys:
            updated_lines.append(f"{k}={v}")

    # Write atomically
    temp_env = resolved_path.with_suffix(".tmp")
    temp_env.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
    temp_env.replace(resolved_path)


def load_and_group_history(
    csv_path: pathlib.Path, max_records: int
) -> dict[str, list[ViewingRecord]]:
    """Parse Netflix viewing history and group by base title."""
    records = parse_netflix_history(csv_path)
    grouped: dict[str, list[ViewingRecord]] = {}
    for record in records[:max_records]:
        base_title = record.title.split(":")[0].strip()
        if base_title not in grouped:
            grouped[base_title] = []
        grouped[base_title].append(record)
    return grouped
