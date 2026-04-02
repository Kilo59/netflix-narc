"""Persistence utilities for Netflix Narc."""

from __future__ import annotations

from typing import TYPE_CHECKING

from netflix_narc.parser import parse_netflix_history
from netflix_narc.settings import RatingProviderType

if TYPE_CHECKING:
    import pathlib

    from pydantic import SecretStr

    from netflix_narc.parser import ViewingRecord


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


def update_env_file(
    provider: RatingProviderType, api_key: SecretStr, env_path: pathlib.Path
) -> None:
    """Update the .env file with new provider settings, deduplicating keys."""
    env_lines: list[str] = []
    if env_path.exists():
        env_lines = env_path.read_text().splitlines()

    # Map prefix to new value
    new_values = {
        "ACTIVE_RATING_PROVIDER": str(provider),
    }
    if provider == RatingProviderType.CSM:
        new_values["CSM_API_KEY"] = api_key.get_secret_value()
    elif provider == RatingProviderType.OMDB:
        new_values["OMDB_API_KEY"] = api_key.get_secret_value()

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
    temp_env = env_path.with_suffix(".tmp")
    temp_env.write_text("\n".join(updated_lines) + "\n")
    temp_env.replace(env_path)


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
