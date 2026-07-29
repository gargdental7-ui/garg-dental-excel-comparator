"""Thin wrapper over Supabase Storage's REST API using the service_role
(secret) key, which bypasses RLS - this is intentional and safe here
because, same as _db.py, the FastAPI backend is the sole caller and every
route enforces its own authorization before reaching these functions.
Never expose SUPABASE_SERVICE_ROLE_KEY (or the legacy service_role JWT)
to the frontend; only the publishable/anon key would ever be safe
client-side, and nothing in this app talks to Supabase from the browser.
"""
import os
import time

import httpx

from app.exceptions import AppError

MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 1.0


class StorageError(AppError):
    def __init__(self, detail: str):
        super().__init__(f"A file storage operation failed: {detail}")


def _base_url() -> str:
    url = os.environ.get("SUPABASE_URL")
    if not url:
        raise RuntimeError("SUPABASE_URL environment variable is not set.")
    return url.rstrip("/")


def _service_role_key() -> str:
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY environment variable is not set.")
    return key


def _headers() -> dict:
    key = _service_role_key()
    return {"Authorization": f"Bearer {key}", "apikey": key}


def _request_with_retry(method: str, url: str, error_context: str, **kwargs) -> httpx.Response:
    """A network blip talking to Supabase Storage shouldn't turn into a
    lost quotation/master-Excel save - retries transient failures (network
    errors, 5xx) a couple of times before giving up. 4xx responses (bad
    request, not found, etc.) are never retried since retrying won't change
    the outcome."""
    last_exc: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = httpx.request(method, url, timeout=30.0, **kwargs)
        except httpx.HTTPError as exc:
            last_exc = exc
        else:
            if response.status_code < 500:
                return response
            last_exc = StorageError(f"{error_context} failed ({response.status_code})")
        if attempt < MAX_ATTEMPTS:
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)
    raise last_exc if isinstance(last_exc, StorageError) else StorageError(f"{error_context}: {last_exc}")


def upload(bucket: str, path: str, content: bytes, content_type: str) -> None:
    """Uploads (or overwrites, via upsert) content to bucket/path."""
    url = f"{_base_url()}/storage/v1/object/{bucket}/{path}"
    headers = {**_headers(), "Content-Type": content_type, "x-upsert": "true"}
    response = _request_with_retry("PUT", url, f"upload to {bucket}/{path}", content=content, headers=headers)
    if response.status_code >= 400:
        raise StorageError(f"upload to {bucket}/{path} failed ({response.status_code})")


def download(bucket: str, path: str) -> bytes:
    url = f"{_base_url()}/storage/v1/object/{bucket}/{path}"
    response = _request_with_retry("GET", url, f"download of {bucket}/{path}", headers=_headers())
    if response.status_code >= 400:
        raise StorageError(f"download of {bucket}/{path} failed ({response.status_code})")
    return response.content


def delete(bucket: str, path: str) -> None:
    url = f"{_base_url()}/storage/v1/object/{bucket}/{path}"
    response = _request_with_retry("DELETE", url, f"delete of {bucket}/{path}", headers=_headers())
    if response.status_code >= 400:
        raise StorageError(f"delete of {bucket}/{path} failed ({response.status_code})")
