"""
Prediction API tests.

These cover the error/contract paths that don't require an LLM call: generating
without a completed analysis, and retrieving a prediction that doesn't exist.
"""

import pytest
from httpx import AsyncClient

PDF_BYTES = b"%PDF-1.4\nfake pdf content for tests\n%%EOF"


async def _upload(client: AsyncClient, headers: dict) -> str:
    resp = await client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files={"file": ("exam.pdf", PDF_BYTES, "application/pdf")},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_generate_requires_completed_analysis(client, auth):
    """Generating before any analysis should fail (no completed analysis)."""
    doc_id = await _upload(client, auth["headers"])
    resp = await client.post(f"/api/v1/predictions/{doc_id}/generate", headers=auth["headers"])
    assert resp.status_code == 500
    assert "analysis" in resp.json()["message"].lower()


@pytest.mark.asyncio
async def test_get_prediction_404_when_none(client, auth):
    doc_id = await _upload(client, auth["headers"])
    resp = await client.get(f"/api/v1/predictions/{doc_id}", headers=auth["headers"])
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_confidence_404_when_none(client, auth):
    doc_id = await _upload(client, auth["headers"])
    resp = await client.get(f"/api/v1/predictions/{doc_id}/confidence", headers=auth["headers"])
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_generate_requires_auth(client, auth):
    doc_id = await _upload(client, auth["headers"])
    resp = await client.post(f"/api/v1/predictions/{doc_id}/generate")
    assert resp.status_code in (401, 403)
