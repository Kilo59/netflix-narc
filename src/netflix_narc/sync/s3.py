"""S3-compatible object storage backend (Cloudflare R2, AWS S3, MinIO)."""

from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
from typing import TYPE_CHECKING, override

if TYPE_CHECKING:
    from collections.abc import Generator

    from pydantic import SecretStr

import urllib.parse

import httpx

from netflix_narc.sync.backend import (
    StorageAuthError,
    StorageBackend,
    StorageBackendError,
    StorageConnectionError,
)
from netflix_narc.sync.models import SyncBundle, SyncManifest


def _canonicalize_query(query_bytes: bytes) -> str:
    """Construct AWS SigV4 canonical query string by sorting and RFC 3986 encoding parameters."""
    if not query_bytes:
        return ""
    query_str = query_bytes.decode("utf-8")
    params = urllib.parse.parse_qsl(query_str, keep_blank_values=True)
    encoded_params = [
        (urllib.parse.quote(k, safe="~"), urllib.parse.quote(v, safe="~")) for k, v in params
    ]
    encoded_params.sort(key=lambda pair: (pair[0], pair[1]))
    return "&".join(f"{k}={v}" for k, v in encoded_params)


STATUS_NOT_FOUND = 404
STATUS_OK = 200
STATUS_UNAUTHORIZED = 401
STATUS_FORBIDDEN = 403


class S3SigV4Auth(httpx.Auth):
    """httpx Auth implementation for AWS Signature Version 4 (SigV4)."""

    def __init__(
        self,
        access_key_id: str,
        secret_access_key: str,
        region: str = "us-east-1",
        service: str = "s3",
    ) -> None:
        """Initialize SigV4 credentials and scope."""
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.region = region
        self.service = service

    @override
    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response]:
        """Sign request headers using AWS SigV4."""
        now = dt.datetime.now(dt.UTC)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")

        request.headers["x-amz-date"] = amz_date

        content = request.content
        payload_hash = (
            hashlib.sha256(content).hexdigest() if content else hashlib.sha256(b"").hexdigest()
        )
        request.headers["x-amz-content-sha256"] = payload_hash

        url = request.url
        request.headers["host"] = url.netloc.decode("ascii")

        canonical_headers = ""
        signed_headers_list = []
        for k in sorted(request.headers.keys()):
            lk = k.lower()
            if lk in ("host", "x-amz-date", "x-amz-content-sha256"):
                val = " ".join(request.headers[k].split())
                canonical_headers += f"{lk}:{val}\n"
                signed_headers_list.append(lk)
        signed_headers = ";".join(signed_headers_list)

        canonical_uri = url.raw_path.decode("ascii").split("?")[0] or "/"
        canonical_query = _canonicalize_query(url.query)

        canonical_request = (
            f"{request.method}\n{canonical_uri}\n{canonical_query}\n"
            f"{canonical_headers}\n{signed_headers}\n{payload_hash}"
        )
        credential_scope = f"{date_stamp}/{self.region}/{self.service}/aws4_request"
        string_to_sign = (
            f"AWS4-HMAC-SHA256\n{amz_date}\n{credential_scope}\n"
            f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        )

        def _sign(key: bytes, msg: str) -> bytes:
            return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

        k_date = _sign(f"AWS4{self.secret_access_key}".encode(), date_stamp)
        k_region = _sign(k_date, self.region)
        k_service = _sign(k_region, self.service)
        k_signing = _sign(k_service, "aws4_request")

        signature = hmac.new(k_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

        authorization_header = (
            f"AWS4-HMAC-SHA256 Credential={self.access_key_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )
        request.headers["authorization"] = authorization_header

        yield request


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
        """Create or return httpx AsyncClient configured with AWS SigV4 Auth."""
        if self._client is not None:
            return self._client

        auth: httpx.Auth | None = None
        if self.access_key_id and self.secret_access_key:
            ak = self.access_key_id.get_secret_value().strip()
            sk = self.secret_access_key.get_secret_value().strip()
            if ak and sk:
                auth = S3SigV4Auth(ak, sk)
        return httpx.AsyncClient(auth=auth, timeout=15.0)

    @override
    async def initialize(self) -> None:
        """Verify endpoint connectivity and credentials."""
        url = self._get_url("manifest.json")
        client = self._create_client()
        should_close = self._client is None
        try:
            res = await client.head(url)
        except httpx.HTTPError as exc:
            msg = f"Failed to connect to S3 endpoint: {exc}"
            raise StorageConnectionError(msg) from exc
        finally:
            if should_close:
                await client.aclose()

        if res.status_code in (STATUS_UNAUTHORIZED, STATUS_FORBIDDEN):
            msg = f"S3 authorization failed ({res.status_code}): Access Denied"
            raise StorageAuthError(msg)
        if res.status_code not in (STATUS_OK, STATUS_NOT_FOUND):
            msg = f"S3 endpoint returned unexpected status: {res.status_code}"
            raise StorageBackendError(msg)

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
            return res.status_code in (STATUS_OK, STATUS_NOT_FOUND)
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
        except httpx.HTTPError as exc:
            msg = f"Failed to fetch S3 manifest: {exc}"
            raise StorageBackendError(msg) from exc
        finally:
            if should_close:
                await client.aclose()

        if res.status_code in (STATUS_UNAUTHORIZED, STATUS_FORBIDDEN):
            msg = f"S3 authorization failed ({res.status_code}): Access Denied"
            raise StorageAuthError(msg)
        if res.status_code == STATUS_NOT_FOUND:
            return None

        try:
            res.raise_for_status()
            return SyncManifest.model_validate(res.json())
        except (httpx.HTTPError, json.JSONDecodeError, ValueError) as exc:
            msg = f"Failed to parse S3 manifest: {exc}"
            raise StorageBackendError(msg) from exc

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
            res_m = await client.put(manifest_url, json=manifest_payload, headers=headers)
        except httpx.HTTPError as exc:
            msg = f"Failed to upload sync bundle to S3: {exc}"
            raise StorageBackendError(msg) from exc
        finally:
            if should_close:
                await client.aclose()

        if res_b.status_code in (STATUS_UNAUTHORIZED, STATUS_FORBIDDEN):
            msg = f"S3 upload authorization failed ({res_b.status_code}): Access Denied"
            raise StorageAuthError(msg)
        if res_m.status_code in (STATUS_UNAUTHORIZED, STATUS_FORBIDDEN):
            msg = f"S3 manifest upload authorization failed ({res_m.status_code}): Access Denied"
            raise StorageAuthError(msg)

        try:
            res_b.raise_for_status()
            res_m.raise_for_status()
        except httpx.HTTPError as exc:
            msg = f"S3 bundle upload returned HTTP error: {exc}"
            raise StorageBackendError(msg) from exc

    @override
    async def download_bundle(self) -> SyncBundle | None:
        """Download bundle.json from S3 bucket."""
        url = self._get_url("bundle.json")
        client = self._create_client()
        should_close = self._client is None
        try:
            res = await client.get(url)
        except httpx.HTTPError as exc:
            msg = f"Failed to download S3 bundle: {exc}"
            raise StorageBackendError(msg) from exc
        finally:
            if should_close:
                await client.aclose()

        if res.status_code in (STATUS_UNAUTHORIZED, STATUS_FORBIDDEN):
            msg = f"S3 download authorization failed ({res.status_code}): Access Denied"
            raise StorageAuthError(msg)
        if res.status_code == STATUS_NOT_FOUND:
            return None

        try:
            res.raise_for_status()
            return SyncBundle.model_validate(res.json())
        except (httpx.HTTPError, json.JSONDecodeError, ValueError) as exc:
            msg = f"Failed to parse S3 bundle: {exc}"
            raise StorageBackendError(msg) from exc
