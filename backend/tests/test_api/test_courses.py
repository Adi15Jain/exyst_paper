"""
Course API tests — CRUD, ownership isolation, and the document relationship.
"""

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_login

PDF_BYTES = b"%PDF-1.4\nfake pdf content for tests\n%%EOF"


async def _create_course(client: AsyncClient, headers: dict, name: str = "Machine Learning"):
    return await client.post(
        "/api/v1/courses/",
        headers=headers,
        json={"name": name, "code": "EAI602", "semester": "6th"},
    )


@pytest.mark.asyncio
async def test_create_course(client: AsyncClient, auth: dict):
    resp = await _create_course(client, auth["headers"])
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "Machine Learning"
    assert body["code"] == "EAI602"
    assert body["document_count"] == 0


@pytest.mark.asyncio
async def test_create_course_requires_auth(client: AsyncClient):
    resp = await client.post("/api/v1/courses/", json={"name": "X"})
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_course_rejects_empty_name(client: AsyncClient, auth: dict):
    resp = await client.post("/api/v1/courses/", headers=auth["headers"], json={"name": ""})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_courses(client: AsyncClient, auth: dict):
    await _create_course(client, auth["headers"], name="Physics")
    await _create_course(client, auth["headers"], name="Chemistry")

    resp = await client.get("/api/v1/courses/", headers=auth["headers"])
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert {c["name"] for c in body["courses"]} == {"Physics", "Chemistry"}


@pytest.mark.asyncio
async def test_update_course_leaves_omitted_fields_alone(client: AsyncClient, auth: dict):
    created = (await _create_course(client, auth["headers"])).json()

    resp = await client.patch(
        f"/api/v1/courses/{created['id']}",
        headers=auth["headers"],
        json={"name": "Advanced ML"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Advanced ML"
    # `code` wasn't sent — a partial update must not blank it out.
    assert body["code"] == "EAI602"


@pytest.mark.asyncio
async def test_course_ownership_isolation(client: AsyncClient, auth: dict):
    created = (await _create_course(client, auth["headers"])).json()
    other = await register_and_login(client)

    assert (
        await client.get(f"/api/v1/courses/{created['id']}", headers=other["headers"])
    ).status_code == 404
    assert (
        await client.patch(
            f"/api/v1/courses/{created['id']}",
            headers=other["headers"],
            json={"name": "hijacked"},
        )
    ).status_code == 404
    assert (
        await client.delete(f"/api/v1/courses/{created['id']}", headers=other["headers"])
    ).status_code == 404


@pytest.mark.asyncio
async def test_upload_files_document_under_course(client: AsyncClient, auth: dict):
    course = (await _create_course(client, auth["headers"])).json()

    resp = await client.post(
        "/api/v1/documents/upload",
        headers=auth["headers"],
        files={"file": ("exam.pdf", PDF_BYTES, "application/pdf")},
        data={"course_id": course["id"]},
    )
    assert resp.status_code == 201, resp.text

    # The course now reports one paper.
    detail = await client.get(f"/api/v1/courses/{course['id']}", headers=auth["headers"])
    assert detail.json()["document_count"] == 1


@pytest.mark.asyncio
async def test_cannot_file_a_paper_into_someone_elses_course(client: AsyncClient, auth: dict):
    """Filing into another user's course would inject a paper into their corpus."""
    course = (await _create_course(client, auth["headers"])).json()
    other = await register_and_login(client)

    resp = await client.post(
        "/api/v1/documents/upload",
        headers=other["headers"],
        files={"file": ("exam.pdf", PDF_BYTES, "application/pdf")},
        data={"course_id": course["id"]},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_documents_can_be_filtered_by_course(client: AsyncClient, auth: dict):
    course = (await _create_course(client, auth["headers"])).json()

    await client.post(
        "/api/v1/documents/upload",
        headers=auth["headers"],
        files={"file": ("filed.pdf", PDF_BYTES, "application/pdf")},
        data={"course_id": course["id"]},
    )
    # An unfiled paper, which must not show up under the course.
    await client.post(
        "/api/v1/documents/upload",
        headers=auth["headers"],
        files={"file": ("unfiled.pdf", b"%PDF-1.4\nother\n%%EOF", "application/pdf")},
    )

    resp = await client.get(
        f"/api/v1/documents/?course_id={course['id']}", headers=auth["headers"]
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["documents"][0]["original_filename"] == "filed.pdf"


@pytest.mark.asyncio
async def test_deleting_a_course_keeps_its_documents(client: AsyncClient, auth: dict):
    """
    Deleting a course must NOT delete the papers filed under it — they're just
    unfiled. Losing a semester of uploads to a tidy-up would be unforgivable.
    """
    course = (await _create_course(client, auth["headers"])).json()
    up = await client.post(
        "/api/v1/documents/upload",
        headers=auth["headers"],
        files={"file": ("exam.pdf", PDF_BYTES, "application/pdf")},
        data={"course_id": course["id"]},
    )
    doc_id = up.json()["id"]

    resp = await client.delete(f"/api/v1/courses/{course['id']}", headers=auth["headers"])
    assert resp.status_code == 204

    # Document survives, now unfiled.
    doc = await client.get(f"/api/v1/documents/{doc_id}", headers=auth["headers"])
    assert doc.status_code == 200
    assert doc.json()["course_id"] is None
