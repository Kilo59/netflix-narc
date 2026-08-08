"""Meta-tests that validate project-level configuration consistency."""

from __future__ import annotations

import pathlib
import re

import pytest


@pytest.fixture()
def pyproject_ruff_version() -> str:
    """Extract the ruff version constraint from pyproject.toml dependency-groups."""
    pyproject = pathlib.Path(__file__).parent.parent / "pyproject.toml"
    content = pyproject.read_text(encoding="utf-8")
    match = re.search(r'"ruff>=([^"]+)"', content)
    if not match:
        msg = "Could not find ruff version in pyproject.toml [dependency-groups]"
        raise AssertionError(msg)
    return match.group(1)


@pytest.fixture()
def precommit_ruff_version() -> str:
    """Extract the ruff version from .pre-commit-config.yaml."""
    precommit = pathlib.Path(__file__).parent.parent / ".pre-commit-config.yaml"
    content = precommit.read_text(encoding="utf-8")
    match = re.search(r"astral-sh/ruff-pre-commit.*?rev:\s*\"v([^\"]+)\"", content, re.DOTALL)
    if not match:
        msg = "Could not find ruff version in .pre-commit-config.yaml"
        raise AssertionError(msg)
    return match.group(1)


def test_ruff_version_in_sync(
    pyproject_ruff_version: str,
    precommit_ruff_version: str,
) -> None:
    """The ruff version in pyproject.toml must match .pre-commit-config.yaml.

    This prevents lint drift where the pre-commit hook and `uv run ruff`
    use different rule sets, producing inconsistent CI results.
    """
    assert pyproject_ruff_version == precommit_ruff_version, (
        f"Ruff version mismatch!\n"
        f"  pyproject.toml [dependency-groups.dev]: ruff>={pyproject_ruff_version}\n"
        f"  .pre-commit-config.yaml rev:            v{precommit_ruff_version}\n"
        f"Update one to match the other."
    )


def test_package_data_includes_tcss() -> None:
    """Ensure setuptools package-data includes .tcss files so narc.tcss is bundled in wheels."""
    pyproject = pathlib.Path(__file__).parent.parent / "pyproject.toml"
    content = pyproject.read_text(encoding="utf-8")
    assert "[tool.setuptools.package-data]" in content, (
        "pyproject.toml must configure [tool.setuptools.package-data] to bundle narc.tcss"
    )
    assert "*.tcss" in content, (
        "pyproject.toml [tool.setuptools.package-data] must include '*.tcss'"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
