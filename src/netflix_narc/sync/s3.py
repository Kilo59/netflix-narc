"""S3-compatible object storage backend (Cloudflare R2, AWS S3, MinIO)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, override

if TYPE_CHECKING:
    from pydantic import SecretStr

import httpx

from netflix_narc.sync.backend import StorageBackend, StorageBackendError
from netflix_narc.sync.models import SyncBundle, SyncManifest

STATUS_NOT_FOUND = 404
STATUS_OK = 200
STATUS_FORBIDDEN = 403


class S3StorageBackend(StorageBackend):
    """Storage backend for S3-compatible object storage (AWS S3, Cloudflare R2, MinIO)."""

    def __init__(
        self,
        endpoint_url: str,
        bucket_name: str,
        access_key_id: SecretStr,
        secret_access_key: SecretStr,
        prefix: str = "netflix-narc",
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize S3 storage backend."""
        self.endpoint_url = endpoint_url.rstrip("/")
        self.bucket_name = bucket_name
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.prefix = prefix.strip("/")
        self._client = client

    def _get_url(self, key: str) -> str:
        """Construct resource URL."""
        rel_key = f"{self.prefix}/{key.lstrip('/')}" if self.prefix else key.lstrip("/")
        return f"{self.endpoint_url}/{self.bucket_name}/{rel_key}"

    def _create_client(self) -> httpx.AsyncClient:
        """Create or return httpx AsyncClient."""
        if self._client is not None:
            return self._client
        return httpx.AsyncClient(timeout=15.0)

    @override
    async def initialize(self) -> None:
        """Verify endpoint connectivity."""
        url = self._get_url("manifest.json")
        client = self._create_client()
        should_close = self._client is None
        try:
            res = await client.head(url)
            if res.status_code not in (STATUS_OK, STATUS_NOT_FOUND):
                msg = f"S3 endpoint returned unexpected status: {res.status_code}"
                raise StorageBackendError(msg)
        except httpx.HTTPError as exc:
            msg = f"Failed to connect to S3 endpoint: {exc}"
            raise StorageBackendError(msg) from exc
        finally:
            if should_close:
                await client.aclose()

    @override
    async def test_connection(self) -> bool:
        """Test read access to endpoint."""
        url = self._get_url(".test_ping")
        client = self._create_client()
        should_close = self._client is None
        try:
            res = await client.head(url)
        except httpx.HTTPError:
            return False
        else:
            return res.status_code in (STATUS_OK, STATUS_NOT_FOUND, STATUS_FORBIDDEN)
        finally:
            if should_close:
                await client.aclose()

    @override
    async def get_manifest(self) -> SyncManifest | None:
        """Retrieve manifest.json from S3 bucket."""
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
            msg = f"Failed to fetch or parse S3 manifest: {exc}"
            raise StorageBackendError(msg) from exc
        finally:
            if should_close:
                await client.aclose()

    @override
    async def upload_bundle(self, bundle: SyncBundle) -> None:
        """Upload bundle.json and manifest.json to S3 bucket."""
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
            msg = f"Failed to upload sync bundle to S3: {exc}"
            raise StorageBackendError(msg) from exc
        finally:
            if should_close:
                await client.aclose()

    @override
    async def download_bundle(self) -> SyncBundle | None:
        """Download bundle.json from S3 bucket."""
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
            msg = f"Failed to download or parse S3 bundle: {exc}"
            raise StorageBackendError(msg) from exc
        finally:
            if should_close:
                await client.aclose()
