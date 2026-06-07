"""
API endpoint tests.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Health check should return 200 with status info."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "checks" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_docs_available(client: AsyncClient):
    """OpenAPI docs should be accessible."""
    response = await client.get("/docs")
    assert response.status_code == 200
