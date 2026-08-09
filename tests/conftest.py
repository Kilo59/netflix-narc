"""Shared pytest fixtures for netflix-narc tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest
from pydantic import SecretStr

from netflix_narc.settings import Settings
from netflix_narc.sync.local_folder import LocalStorageBackend
from netflix_narc.sync.s3 import S3StorageBackend
from netflix_narc.sync.webdav import WebDAVStorageBackend

if TYPE_CHECKING:
    import pathlib

    import respx

    from netflix_narc.sync.backend import StorageBackend


@pytest.fixture()
def fake_settings() -> Settings:
    """Return a Settings instance with fake API keys and no real .env file.

    The `_env_file=None` kwarg prevents pydantic-settings from loading the
    real .env file, ensuring tests are hermetic.

    In tests that instantiate API clients, pass `cache_dir=tmp_path` directly
    to the client constructor to sandbox hishel's sqlite writes.
    """
    return Settings(
        csm_api_key=SecretStr("fake-csm-key"),
        omdb_api_key=SecretStr("fake-omdb-key"),
        tmdb_api_key=SecretStr("fake-tmdb-key"),
        _env_file=None,  # type: ignore[call-arg]
    )


@pytest.fixture()
def omdb_response_payload() -> dict[str, str]:
    """Return a canonical OMDb API success response payload.

    Matches the real OMDb JSON shape. Use this as a baseline and override
    individual fields in tests that need specific values.
    """
    return {
        "Title": "The Matrix",
        "Year": "1999",
        "Rated": "R",
        "Released": "31 Mar 1999",
        "Genre": "Action, Sci-Fi",
        "imdbRating": "8.7",
        "imdbID": "tt0133093",
        "Type": "movie",
        "Response": "True",
    }


@pytest.fixture()
def csm_response_payload() -> dict[str, object]:
    """Return a canonical CSM API success response payload.

    Matches the expected CSM JSON shape. Use as a baseline in CSM client tests.
    """
    return {
        "data": [
            {
                "id": "123",
                "title": "The Matrix",
                "age": 14,
                "rating": 4,
                "categories": {
                    "violence": 3,
                    "language": 2,
                    "sexy_stuff": 1,
                },
            }
        ]
    }


@pytest.fixture(params=["local_folder", "s3", "webdav"])
async def storage_backend(
    request: pytest.FixtureRequest,
    tmp_path: pathlib.Path,
    respx_mock: respx.MockRouter,
) -> StorageBackend:
    """Parametrized fixture providing each initialized StorageBackend implementation."""
    match request.param:
        case "local_folder":
            sync_dir = tmp_path / "sync_folder"
            backend_local = LocalStorageBackend(sync_dir)
            await backend_local.initialize()
            return backend_local

        case "s3":
            url_prefix = "https://r2.cloudflarestorage.com/my-sync-bucket/narc-data/"
            respx_mock.head(url_prefix + "manifest.json").respond(status_code=404)

            client = httpx.AsyncClient()
            backend_s3 = S3StorageBackend(
                endpoint_url="https://r2.cloudflarestorage.com",
                bucket_name="my-sync-bucket",
                access_key_id=SecretStr("fake-key"),
                secret_access_key=SecretStr("fake-secret"),
                prefix="narc-data",
                client=client,
            )
            await backend_s3.initialize()
            return backend_s3

        case "webdav":
            base_url = "https://nextcloud.example.com/remote.php/dav/files/user/netflix-narc/"
            respx_mock.request("PROPFIND", base_url).respond(status_code=200)

            client = httpx.AsyncClient()
            backend_webdav = WebDAVStorageBackend(
                webdav_url="https://nextcloud.example.com/remote.php/dav/files/user",
                username="user",
                password=SecretStr("secret-pass"),
                remote_path="netflix-narc",
                client=client,
            )
            await backend_webdav.initialize()
            return backend_webdav

        case _:
            msg = f"Unknown backend parameter: {request.param}"
            raise ValueError(msg)
