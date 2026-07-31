"""API test for the dev token endpoint. Requires PyJWT and FastAPI (CI)."""
from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.asyncio


async def test_dev_token_endpoint_issues_verifiable_token() -> None:
    from eka.api.app import create_app
    from eka.api.security import get_token_verifier
    from eka.config import Settings

    app = create_app(Settings(environment="development"))
    tenant_id = str(uuid.uuid4())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/token",
            json={"tenant_id": tenant_id, "subject": "alice", "roles": ["admin"]},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]

    identity = get_token_verifier().verify(body["access_token"])
    assert str(identity.tenant_id) == tenant_id
    assert identity.has_role("admin")
