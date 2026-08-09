"""Meta-tests that validate project-level configuration consistency."""

from __future__ import annotations

import pathlib
import re
import tomllib

import pytest
from pydantic_settings import SettingsConfigDict

from netflix_narc.settings import Settings


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
    with pyproject.open("rb") as f:
        data = tomllib.load(f)

    package_data = data.get("tool", {}).get("setuptools", {}).get("package-data")
    assert package_data is not None, (
        "pyproject.toml must configure [tool.setuptools.package-data] to bundle narc.tcss"
    )

    has_tcss = any(
        isinstance(v, list) and any("*.tcss" in item for item in v if isinstance(item, str))
        for v in package_data.values()
    )
    assert has_tcss, "pyproject.toml [tool.setuptools.package-data] must include '*.tcss'"

    netflix_narc_patterns = package_data.get("netflix_narc")
    assert isinstance(netflix_narc_patterns, list), (
        "pyproject.toml [tool.setuptools.package-data] entry for 'netflix_narc' must be a list"
    )

    has_netflix_narc_tcss = any(
        isinstance(item, str) and "*.tcss" in item for item in netflix_narc_patterns
    )
    assert has_netflix_narc_tcss, (
        "pyproject.toml [tool.setuptools.package-data] entry for 'netflix_narc' must "
        "explicitly include a '*.tcss' pattern so netflix_narc's CSS is bundled in wheels"
    )


@pytest.mark.parametrize(
    ("raw_input", "expected"),
    [
        (None, None),
        ((10, 14), (10, 14)),
        (("8", "12"), (8, 12)),
        ([7, 13], (7, 13)),
        (["6", "11"], (6, 11)),
        ("10", (10, 10)),
        (" 8 - 12 ", (8, 12)),
    ],
)
def test_parse_child_age_range_valid(raw_input: object, expected: tuple[int, int] | None) -> None:
    """Settings.parse_child_age_range converts valid formats to tuple[int, int]."""
    res = Settings.parse_child_age_range(raw_input)
    assert res == expected


@pytest.mark.parametrize(
    "invalid_input",
    [
        "no_numbers_here",
        12345,
        ["invalid", "data"],
        (1,),
        object(),
    ],
)
def test_parse_child_age_range_invalid_raises(invalid_input: object) -> None:
    """Settings.parse_child_age_range raises ValueError on invalid formats."""
    with pytest.raises(ValueError, match=r"Invalid age range format|Could not parse age range"):
        Settings.parse_child_age_range(invalid_input)


def test_get_env_file_path_resolution(tmp_path: pathlib.Path) -> None:
    """Settings.get_env_file_path returns custom path when model_config env_file is set."""
    custom_env = tmp_path / "custom.env"

    class CustomSettings(Settings):
        model_config = SettingsConfigDict(env_file=custom_env)

    s = CustomSettings()
    assert s.get_env_file_path() == custom_env


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
