"""Tests for the .env persistence logic in netflix_narc.persistence."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pydantic import SecretStr

from netflix_narc.persistence import update_env_file
from netflix_narc.settings import RatingProviderType

if TYPE_CHECKING:
    import pathlib


def test_update_env_file_deduplication(tmp_path: pathlib.Path) -> None:
    """Test that update_env_file updates existing keys and doesn't duplicate them."""
    env_file = tmp_path / ".env"

    # 1. Initial state
    env_file.write_text("EXISTING_VAR=val\nACTIVE_RATING_PROVIDER=csm\nCSM_API_KEY=old-key\n")

    # 2. Update to OMDB
    update_env_file(RatingProviderType.OMDB, SecretStr("new-omdb-key"), env_path=env_file)

    content = env_file.read_text()
    assert "EXISTING_VAR=val" in content
    assert "ACTIVE_RATING_PROVIDER=omdb" in content
    assert "OMDB_API_KEY=new-omdb-key" in content
    # Ensure no duplicates of ACTIVE_RATING_PROVIDER
    assert content.count("ACTIVE_RATING_PROVIDER") == 1
    # Old CSM key should still be there (we don't delete keys for other providers)
    assert "CSM_API_KEY=old-key" in content


def test_update_env_file_preserves_formatting(tmp_path: pathlib.Path) -> None:
    """Test that comments and blank lines are preserved."""
    env_file = tmp_path / ".env"
    initial_content = (
        "# My Config\n\nACTIVE_RATING_PROVIDER=omdb\n# API Keys below\nOMDB_API_KEY=old-key\n"
    )
    env_file.write_text(initial_content)

    update_env_file(RatingProviderType.OMDB, SecretStr("new-key"), env_path=env_file)

    content = env_file.read_text()
    assert "# My Config" in content
    assert "# API Keys below" in content
    assert "OMDB_API_KEY=new-key" in content
    assert content.count("OMDB_API_KEY") == 1


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
