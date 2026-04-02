"""Meta-tests that validate project-level configuration consistency."""

from __future__ import annotations

import pathlib
import re

import pytest


def _get_ruff_version_from_pyproject() -> str:
    """Extract the ruff version constraint from pyproject.toml dependency-groups."""
    pyproject = pathlib.Path(__file__).parent.parent / "pyproject.toml"
    content = pyproject.read_text(encoding="utf-8")
    # Match e.g. `"ruff>=0.15.5"` in the dev dependency group
    match = re.search(r'"ruff>=([^"]+)"', content)
    if not match:
        msg = "Could not find ruff version in pyproject.toml [dependency-groups]"
        raise AssertionError(msg)
    return match.group(1)


def _get_ruff_version_from_precommit() -> str:
    """Extract the ruff version from .pre-commit-config.yaml."""
    precommit = pathlib.Path(__file__).parent.parent / ".pre-commit-config.yaml"
    content = precommit.read_text(encoding="utf-8")
    # Match e.g. `rev: "v0.15.8"` under astral-sh/ruff-pre-commit
    match = re.search(r"astral-sh/ruff-pre-commit.*?rev:\s*\"v([^\"]+)\"", content, re.DOTALL)
    if not match:
        msg = "Could not find ruff version in .pre-commit-config.yaml"
        raise AssertionError(msg)
    return match.group(1)


def test_ruff_version_in_sync() -> None:
    """The ruff version in pyproject.toml must match .pre-commit-config.yaml.

    This prevents lint drift where the pre-commit hook and `uv run ruff`
    use different rule sets, producing inconsistent CI results.
    """
    pyproject_version = _get_ruff_version_from_pyproject()
    precommit_version = _get_ruff_version_from_precommit()
    assert pyproject_version == precommit_version, (
        f"Ruff version mismatch!\n"
        f"  pyproject.toml [dependency-groups.dev]: ruff>={pyproject_version}\n"
        f"  .pre-commit-config.yaml rev:            v{precommit_version}\n"
        f"Update one to match the other."
    )


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
