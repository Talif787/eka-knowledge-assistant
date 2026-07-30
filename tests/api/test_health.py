"""API test for liveness. Requires the app dependencies to be installed."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.asyncio


async def test_liveness_ok() -> None:
    from eka.api.app import create_app
    from eka.config import Settings

    app = create_app(Settings(environment="development"))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
