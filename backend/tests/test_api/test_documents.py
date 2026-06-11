"""
Document API tests — upload, list, retrieve, ownership isolation.

The upload endpoint stores bytes and validates extension/size only (it does not
parse the PDF), so a small byte blob with a .pdf name is sufficient here.
"""

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_login

PDF_BYTES = b"%PDF-1.4\nfake pdf content for tests\n%%EOF"


async def _upload(client: AsyncClient, headers: dict, name: str = "exam.pdf", content: bytes = PDF_BYTES):
    return await client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files={"file": (name, content, "application/pdf")},
    )


@pytest.mark.asyncio
async def test_upload_requires_auth(client: AsyncClient):
    resp = await _upload(client, headers={})
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_upload_success(client: AsyncClient, auth: dict):
    resp = await _upload(client, auth["headers"])
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "pending"
    assert body["file_size_bytes"] == len(PDF_BYTES)
    assert "id" in body


@pytest.mark.asyncio
async def test_upload_rejects_non_pdf(client: AsyncClient, auth: dict):
    resp = await _upload(client, auth["headers"], name="notes.txt", content=b"hello")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_upload_rejects_empty_file(client: AsyncClient, auth: dict):
    resp = await _upload(client, auth["headers"], content=b"")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_documents_includes_upload(client: AsyncClient, auth: dict):
    up = await _upload(client, auth["headers"])
    doc_id = up.json()["id"]

    resp = await client.get("/api/v1/documents/", headers=auth["headers"])
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert any(d["id"] == doc_id for d in body["documents"])


@pytest.mark.asyncio
async def test_get_document(client: AsyncClient, auth: dict):
    up = await _upload(client, auth["headers"])
    doc_id = up.json()["id"]

    resp = await client.get(f"/api/v1/documents/{doc_id}", headers=auth["headers"])
    assert resp.status_code == 200
    assert resp.json()["id"] == doc_id


@pytest.mark.asyncio
async def test_get_missing_document_404(client: AsyncClient, auth: dict):
    missing = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/api/v1/documents/{missing}", headers=auth["headers"])
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_document_ownership_isolation(client: AsyncClient, auth: dict):
    """User B must not be able to read User A's document."""
    up = await _upload(client, auth["headers"])
    doc_id = up.json()["id"]

    other = await register_and_login(client)
    resp = await client.get(f"/api/v1/documents/{doc_id}", headers=other["headers"])
    assert resp.status_code == 404
