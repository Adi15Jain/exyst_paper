"""
Analysis API tests.

The real pipeline calls Gemini, so it is mocked here: the endpoint contract
(202 + PROCESSING record) is tested with a no-op background task, and the
background runner's success/failure persistence is tested directly with a
stubbed pipeline body.
"""

import pytest
from httpx import AsyncClient

from app.api.v1.analysis import analysis_service
from app.core.exceptions import AnalysisError
from app.models import ProcessingStatus
from app.services.analysis_service import AnalysisService
from tests.conftest import register_and_login

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
async def test_run_analysis_returns_202_and_pending_record(client, auth, monkeypatch):
    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(analysis_service, "run_analysis_background", _noop)

    doc_id = await _upload(client, auth["headers"])
    resp = await client.post(f"/api/v1/analysis/{doc_id}/run", headers=auth["headers"])
    assert resp.status_code == 202, resp.text
    assert resp.json()["status"] == "processing"

    status = await client.get(f"/api/v1/analysis/{doc_id}/status", headers=auth["headers"])
    assert status.status_code == 200
    assert status.json()["status"] == "processing"


@pytest.mark.asyncio
async def test_run_analysis_missing_document_404(client, auth, monkeypatch):
    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(analysis_service, "run_analysis_background", _noop)

    missing = "00000000-0000-0000-0000-000000000000"
    resp = await client.post(f"/api/v1/analysis/{missing}/run", headers=auth["headers"])
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_status_404_when_no_analysis(client, auth):
    doc_id = await _upload(client, auth["headers"])
    resp = await client.get(f"/api/v1/analysis/{doc_id}/status", headers=auth["headers"])
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_run_analysis_ownership_isolation(client, auth, monkeypatch):
    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(analysis_service, "run_analysis_background", _noop)

    doc_id = await _upload(client, auth["headers"])
    other = await register_and_login(client)
    resp = await client.post(f"/api/v1/analysis/{doc_id}/run", headers=other["headers"])
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_background_runner_marks_completed(client, auth, monkeypatch):
    """The scheduled background task should persist a COMPLETED analysis on success."""

    async def fake_pipeline(self, analysis, document, progress_callback=None):
        analysis.status = ProcessingStatus.COMPLETED
        analysis.num_papers_found = 2
        document.status = ProcessingStatus.COMPLETED
        return analysis

    # Patch the pipeline body before triggering the run, so the real background
    # task (executed by the test transport) runs end-to-end without an LLM.
    monkeypatch.setattr(AnalysisService, "_run_pipeline", fake_pipeline)

    doc_id = await _upload(client, auth["headers"])
    run = await client.post(f"/api/v1/analysis/{doc_id}/run", headers=auth["headers"])
    assert run.status_code == 202

    status = await client.get(f"/api/v1/analysis/{doc_id}/status", headers=auth["headers"])
    assert status.status_code == 200
    assert status.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_background_runner_persists_failure(client, auth, monkeypatch):
    """A failing pipeline should leave the analysis in FAILED with a message."""

    async def boom_pipeline(self, analysis, document, progress_callback=None):
        raise AnalysisError("pipeline exploded")

    monkeypatch.setattr(AnalysisService, "_run_pipeline", boom_pipeline)

    doc_id = await _upload(client, auth["headers"])
    run = await client.post(f"/api/v1/analysis/{doc_id}/run", headers=auth["headers"])
    assert run.status_code == 202

    status = await client.get(f"/api/v1/analysis/{doc_id}/status", headers=auth["headers"])
    assert status.status_code == 200
    body = status.json()
    assert body["status"] == "failed"
    assert "exploded" in (body["error_message"] or "")
