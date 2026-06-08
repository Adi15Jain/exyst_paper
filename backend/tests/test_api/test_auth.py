import pytest
import uuid
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_register_endpoint(client: AsyncClient):
    random_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": random_email, "password": "password123", "name": "Test User"}
    )
    print("REGISTER RESPONSE:", response.status_code, response.text)
    assert response.status_code == 201
