"""
Document API tests — upload, list, retrieve, ownership isolation.

The upload endpoint stores bytes and validates extension/size only (it does not
parse the PDF), so a small byte blob with a .pdf name is sufficient here.
"""

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_login

PDF_BYTES = b"%PDF-1.4\nfake pdf content for tests\n%%EOF"


async def _upload(
    client: AsyncClient,
    headers: dict,
    name: str = "exam.pdf",
    content: bytes = PDF_BYTES,
):
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


@pytest.mark.asyncio
async def test_reupload_without_analysis_is_not_deduplicated(client: AsyncClient, auth: dict):
    """Dedup only kicks in once a COMPLETED analysis exists to reuse."""
    first = await _upload(client, auth["headers"])
    second = await _upload(client, auth["headers"])

    assert first.json()["id"] != second.json()["id"]
    assert second.json()["deduplicated"] is False


@pytest.mark.asyncio
async def test_reupload_of_analyzed_file_reuses_document(client, auth, monkeypatch):
    """An identical PDF whose analysis already completed is reused, not re-run."""
    from app.models import ProcessingStatus
    from app.services.analysis_service import AnalysisService

    async def fake_pipeline(self, analysis, document, db, progress_callback=None):
        analysis.status = ProcessingStatus.COMPLETED
        document.status = ProcessingStatus.COMPLETED
        return analysis

    monkeypatch.setattr(AnalysisService, "_run_pipeline", fake_pipeline)

    up = await _upload(client, auth["headers"])
    doc_id = up.json()["id"]
    run = await client.post(f"/api/v1/analysis/{doc_id}/run", headers=auth["headers"])
    assert run.status_code == 202

    again = await _upload(client, auth["headers"])
    assert again.status_code == 201
    body = again.json()
    assert body["id"] == doc_id
    assert body["deduplicated"] is True


@pytest.mark.asyncio
async def test_dedup_does_not_cross_users(client, auth, monkeypatch):
    """One user's analyzed file must never be handed to another user."""
    from app.models import ProcessingStatus
    from app.services.analysis_service import AnalysisService

    async def fake_pipeline(self, analysis, document, db, progress_callback=None):
        analysis.status = ProcessingStatus.COMPLETED
        document.status = ProcessingStatus.COMPLETED
        return analysis

    monkeypatch.setattr(AnalysisService, "_run_pipeline", fake_pipeline)

    up = await _upload(client, auth["headers"])
    doc_id = up.json()["id"]
    await client.post(f"/api/v1/analysis/{doc_id}/run", headers=auth["headers"])

    other = await register_and_login(client)
    theirs = await _upload(client, other["headers"])
    assert theirs.json()["id"] != doc_id
    assert theirs.json()["deduplicated"] is False


@pytest.mark.asyncio
async def test_delete_document(client: AsyncClient, auth: dict):
    up = await _upload(client, auth["headers"])
    doc_id = up.json()["id"]

    resp = await client.delete(f"/api/v1/documents/{doc_id}", headers=auth["headers"])
    assert resp.status_code == 204

    gone = await client.get(f"/api/v1/documents/{doc_id}", headers=auth["headers"])
    assert gone.status_code == 404


@pytest.mark.asyncio
async def test_delete_document_with_analysis(client: AsyncClient, auth: dict):
    """Deleting a document must cascade to its analyses (FK would block otherwise)."""
    up = await _upload(client, auth["headers"])
    doc_id = up.json()["id"]

    # Creates a PROCESSING analysis row tied to the document (the background
    # pipeline will fail on the fake PDF, which is fine — the row exists).
    run = await client.post(f"/api/v1/analysis/{doc_id}/run", headers=auth["headers"])
    assert run.status_code == 202

    resp = await client.delete(f"/api/v1/documents/{doc_id}", headers=auth["headers"])
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_requires_ownership(client: AsyncClient, auth: dict):
    up = await _upload(client, auth["headers"])
    doc_id = up.json()["id"]

    other = await register_and_login(client)
    resp = await client.delete(f"/api/v1/documents/{doc_id}", headers=other["headers"])
    assert resp.status_code == 404

    # Still there for the owner.
    still = await client.get(f"/api/v1/documents/{doc_id}", headers=auth["headers"])
    assert still.status_code == 200


@pytest.mark.asyncio
async def test_rename_document(client: AsyncClient, auth: dict):
    up = await _upload(client, auth["headers"])
    doc_id = up.json()["id"]

    resp = await client.patch(
        f"/api/v1/documents/{doc_id}",
        headers=auth["headers"],
        json={"original_filename": "Data Structures 2024.pdf"},
    )
    assert resp.status_code == 200
    assert resp.json()["original_filename"] == "Data Structures 2024.pdf"

    fetched = await client.get(f"/api/v1/documents/{doc_id}", headers=auth["headers"])
    assert fetched.json()["original_filename"] == "Data Structures 2024.pdf"


@pytest.mark.asyncio
async def test_rename_rejects_empty_name(client: AsyncClient, auth: dict):
    up = await _upload(client, auth["headers"])
    doc_id = up.json()["id"]

    resp = await client.patch(
        f"/api/v1/documents/{doc_id}",
        headers=auth["headers"],
        json={"original_filename": ""},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_rename_requires_ownership(client: AsyncClient, auth: dict):
    up = await _upload(client, auth["headers"])
    doc_id = up.json()["id"]

    other = await register_and_login(client)
    resp = await client.patch(
        f"/api/v1/documents/{doc_id}",
        headers=other["headers"],
        json={"original_filename": "hijacked.pdf"},
    )
    assert resp.status_code == 404
