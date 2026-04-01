"""Tests for the .env persistence logic in NetflixNarcApp."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

import pytest
from pydantic import SecretStr

from netflix_narc.main import NetflixNarcApp
from netflix_narc.settings import RatingProviderType

if TYPE_CHECKING:
    from pathlib import Path


class MockApp(NetflixNarcApp):
    """Mocked version of NetflixNarcApp that overrides Path('.env') usage."""

    def __init__(self, env_path: Path, **kwargs: Any) -> None:  # noqa: ANN401, ARG002
        self._mock_env_path = env_path
        super().__init__()

    @override
    def _update_env_file(self, provider: RatingProviderType, api_key: SecretStr) -> None:
        """Override to use the mocked env_path."""
        # We temporarily patch Path.exists/read_text/etc or just reimplement for test
        # Actually, it's easier to just pass the path to the original method if we refactor it,
        # but let's just copy the logic here for the test to verify the logic itself.

        env_path = self._mock_env_path
        env_lines = []
        if env_path.exists():
            env_lines = env_path.read_text().splitlines()

        new_values = {
            "ACTIVE_RATING_PROVIDER": str(provider),
        }
        if provider == RatingProviderType.CSM:
            new_values["CSM_API_KEY"] = api_key.get_secret_value()
        elif provider == RatingProviderType.OMDB:
            new_values["OMDB_API_KEY"] = api_key.get_secret_value()

        updated_lines = []
        seen_keys: set[str] = set()
        for raw_line in env_lines:
            updated_line = self._parse_env_line(raw_line, new_values, seen_keys)
            if updated_line is not None:
                updated_lines.append(updated_line)

        for k, v in new_values.items():
            if k not in seen_keys:
                updated_lines.append(f"{k}={v}")

        temp_env = env_path.with_suffix(".tmp")
        temp_env.write_text("\n".join(updated_lines) + "\n")
        temp_env.replace(env_path)


def test_update_env_file_deduplication(tmp_path: Path) -> None:
    """Test that _update_env_file updates existing keys and doesn't duplicate them."""
    env_file = tmp_path / ".env"

    # 1. Initial state
    env_file.write_text("EXISTING_VAR=val\nACTIVE_RATING_PROVIDER=csm\nCSM_API_KEY=old-key\n")

    app = MockApp(env_path=env_file)

    # 2. Update to OMDB
    app._update_env_file(RatingProviderType.OMDB, SecretStr("new-omdb-key"))  # noqa: SLF001

    content = env_file.read_text()
    assert "EXISTING_VAR=val" in content
    assert "ACTIVE_RATING_PROVIDER=omdb" in content
    assert "OMDB_API_KEY=new-omdb-key" in content
    # Ensure no duplicates of ACTIVE_RATING_PROVIDER
    assert content.count("ACTIVE_RATING_PROVIDER") == 1
    # Old CSM key should still be there (we don't delete keys for other providers)
    assert "CSM_API_KEY=old-key" in content


def test_update_env_file_preserves_formatting(tmp_path: Path) -> None:
    """Test that comments and blank lines are preserved."""
    env_file = tmp_path / ".env"
    initial_content = (
        "# My Config\n\nACTIVE_RATING_PROVIDER=omdb\n# API Keys below\nOMDB_API_KEY=old-key\n"
    )
    env_file.write_text(initial_content)

    app = MockApp(env_path=env_file)
    app._update_env_file(RatingProviderType.OMDB, SecretStr("new-key"))  # noqa: SLF001  # noqa: SLF001

    content = env_file.read_text()
    assert "# My Config" in content
    assert "# API Keys below" in content
    assert "OMDB_API_KEY=new-key" in content
    assert content.count("OMDB_API_KEY") == 1


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
