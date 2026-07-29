"""WebDAV storage backend (Nextcloud, ownCloud, WebDAV servers)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, override

if TYPE_CHECKING:
    from pydantic import SecretStr

import httpx

from netflix_narc.sync.backend import StorageBackend, StorageBackendError
from netflix_narc.sync.models import SyncBundle, SyncManifest

STATUS_NOT_FOUND = 404
STATUS_CREATED = 201
STATUS_METHOD_NOT_ALLOWED = 405


class WebDAVStorageBackend(StorageBackend):
    """Storage backend for WebDAV endpoints (Nextcloud, ownCloud)."""

    def __init__(
        self,
        webdav_url: str,
        username: str,
        password: SecretStr,
        remote_path: str = "netflix-narc",
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize WebDAV storage backend."""
        self.webdav_url = webdav_url.rstrip("/")
        self.username = username
        self.password = password
        self.remote_path = remote_path.strip("/")
        self._client = client

    def _get_url(self, key: str) -> str:
        """Construct full WebDAV resource URL."""
        rel_key = f"{self.remote_path}/{key.lstrip('/')}" if self.remote_path else key.lstrip("/")
        return f"{self.webdav_url}/{rel_key}"

    def _create_client(self) -> httpx.AsyncClient:
        """Create or return httpx AsyncClient configured with Basic Auth."""
        if self._client is not None:
            return self._client
        auth = (self.username, self.password.get_secret_value())
        return httpx.AsyncClient(auth=auth, timeout=15.0)

    @override
    async def initialize(self) -> None:
        """Verify WebDAV connection."""
        url = self._get_url("")
        client = self._create_client()
        should_close = self._client is None
        try:
            res = await client.request("PROPFIND", url, headers={"Depth": "0"})
            if res.status_code == STATUS_NOT_FOUND:
                # Attempt MKCOL to create folder
                mk_res = await client.request("MKCOL", url)
                if mk_res.status_code not in (STATUS_CREATED, STATUS_METHOD_NOT_ALLOWED):
                    msg = f"Failed to create WebDAV directory: {mk_res.status_code}"
                    raise StorageBackendError(msg)
            elif res.status_code not in (200, 207):
                msg = f"WebDAV endpoint returned unexpected status: {res.status_code}"
                raise StorageBackendError(msg)
        except httpx.HTTPError as exc:
            msg = f"Failed to connect to WebDAV endpoint: {exc}"
            raise StorageBackendError(msg) from exc
        finally:
            if should_close:
                await client.aclose()

    @override
    async def test_connection(self) -> bool:
        """Test read authentication with WebDAV endpoint."""
        url = self._get_url("")
        client = self._create_client()
        should_close = self._client is None
        try:
            res = await client.request("PROPFIND", url, headers={"Depth": "0"})
        except httpx.HTTPError:
            return False
        else:
            return res.status_code in (200, 207, STATUS_NOT_FOUND)
        finally:
            if should_close:
                await client.aclose()

    @override
    async def get_manifest(self) -> SyncManifest | None:
        """Fetch manifest.json from WebDAV."""
        url = self._get_url("manifest.json")
        client = self._create_client()
        should_close = self._client is None
        try:
            res = await client.get(url)
            if res.status_code == STATUS_NOT_FOUND:
                return None
            res.raise_for_status()
            return SyncManifest.model_validate(res.json())
        except (httpx.HTTPError, json.JSONDecodeError, ValueError) as exc:
            msg = f"Failed to fetch WebDAV manifest: {exc}"
            raise StorageBackendError(msg) from exc
        finally:
            if should_close:
                await client.aclose()

    @override
    async def upload_bundle(self, bundle: SyncBundle) -> None:
        """Upload bundle.json and manifest.json to WebDAV."""
        await self.initialize()

        bundle_url = self._get_url("bundle.json")
        manifest_url = self._get_url("manifest.json")

        client = self._create_client()
        should_close = self._client is None

        bundle_payload = bundle.model_dump(mode="json")
        manifest = SyncManifest(
            latest_bundle_id="bundle.json",
            last_updated=bundle.timestamp,
            client_id=bundle.client_id,
            version=bundle.version,
        )
        manifest_payload = manifest.model_dump(mode="json")

        headers = {"Content-Type": "application/json"}
        try:
            res_b = await client.put(bundle_url, json=bundle_payload, headers=headers)
            res_b.raise_for_status()

            res_m = await client.put(manifest_url, json=manifest_payload, headers=headers)
            res_m.raise_for_status()
        except httpx.HTTPError as exc:
            msg = f"Failed to upload sync bundle to WebDAV: {exc}"
            raise StorageBackendError(msg) from exc
        finally:
            if should_close:
                await client.aclose()

    @override
    async def download_bundle(self) -> SyncBundle | None:
        """Download bundle.json from WebDAV."""
        url = self._get_url("bundle.json")
        client = self._create_client()
        should_close = self._client is None
        try:
            res = await client.get(url)
            if res.status_code == STATUS_NOT_FOUND:
                return None
            res.raise_for_status()
            return SyncBundle.model_validate(res.json())
        except (httpx.HTTPError, json.JSONDecodeError, ValueError) as exc:
            msg = f"Failed to download WebDAV bundle: {exc}"
            raise StorageBackendError(msg) from exc
        finally:
            if should_close:
                await client.aclose()
