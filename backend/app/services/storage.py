"""
File storage abstraction — local disk or Vercel Blob.

On long-lived hosts uploads go to UPLOAD_DIR on disk. On Vercel the filesystem
is per-invocation (/tmp), so when a BLOB_READ_WRITE_TOKEN is configured uploads
go to Vercel Blob instead and Document.file_path holds the blob URL.

Reads and deletes dispatch on the stored path itself (URL vs local path), so
documents uploaded before a backend switch keep working after it.

Note: Vercel Blob objects are public-but-unguessable (a random suffix is added
to every pathname). Do not log blob URLs.
"""

import asyncio
import os

import httpx

from app.config import get_settings
from app.core.exceptions import DocumentUploadError
from app.core.logging import get_logger

logger = get_logger(__name__)

_BLOB_API_BASE = "https://blob.vercel-storage.com"
_BLOB_API_VERSION = "7"


def _blob_token() -> str | None:
    return os.environ.get("BLOB_READ_WRITE_TOKEN") or None


def blob_storage_enabled() -> bool:
    """True when uploads should go to Vercel Blob instead of local disk."""
    return _blob_token() is not None


async def save_upload(key: str, content: bytes, content_type: str = "application/pdf") -> str:
    """
    Persist an uploaded file and return the path to store on the Document row.

    ``key`` is a relative path like "<user_id>/<timestamp>_<name>". Returns a
    blob URL when blob storage is enabled, otherwise a local filesystem path.
    """
    if blob_storage_enabled():
        return await _blob_put(key, content, content_type)
    return await asyncio.to_thread(_local_write, key, content)


async def read_stored_file(path: str) -> bytes:
    """Read a stored file, whether it lives on local disk or in blob storage."""
    if path.startswith(("http://", "https://")):
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(path)
            response.raise_for_status()
            return response.content
    return await asyncio.to_thread(_local_read, path)


async def delete_stored_file(path: str) -> None:
    """
    Best-effort delete of a stored file. Never raises: the DB row is the
    source of truth and an orphaned file must not block the API operation.
    """
    try:
        if path.startswith(("http://", "https://")):
            await _blob_delete(path)
        else:
            await asyncio.to_thread(_local_delete, path)
    except Exception as e:
        logger.warning("stored_file_delete_failed", error=str(e))


# --- Local disk backend ---


def _local_write(key: str, content: bytes) -> str:
    settings = get_settings()
    file_path = os.path.join(settings.UPLOAD_DIR, key)
    directory = os.path.dirname(file_path)
    os.makedirs(directory, exist_ok=True)

    # Defence in depth: ensure the resolved path stays inside the upload dir.
    upload_root = os.path.realpath(settings.UPLOAD_DIR)
    if os.path.commonpath([os.path.realpath(file_path), upload_root]) != upload_root:
        raise DocumentUploadError("Invalid filename")

    with open(file_path, "wb") as f:
        f.write(content)
    return file_path


def _local_read(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def _local_delete(path: str) -> None:
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


# --- Vercel Blob backend (REST API) ---


async def _blob_put(key: str, content: bytes, content_type: str) -> str:
    token = _blob_token()
    assert token is not None
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.put(
            f"{_BLOB_API_BASE}/{key}",
            content=content,
            headers={
                "authorization": f"Bearer {token}",
                "x-api-version": _BLOB_API_VERSION,
                "x-content-type": content_type,
                # Random suffix makes the public URL unguessable and avoids
                # collisions between re-uploads of the same filename.
                "x-add-random-suffix": "1",
            },
        )
        if response.status_code >= 400:
            logger.error(
                "blob_upload_failed",
                status=response.status_code,
                body=response.text[:500],
            )
            raise DocumentUploadError("File storage is unavailable, try again later")
        return response.json()["url"]


async def _blob_delete(url: str) -> None:
    token = _blob_token()
    if token is None:
        logger.warning("blob_delete_skipped_no_token")
        return
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{_BLOB_API_BASE}/delete",
            json={"urls": [url]},
            headers={
                "authorization": f"Bearer {token}",
                "x-api-version": _BLOB_API_VERSION,
            },
        )
        response.raise_for_status()
