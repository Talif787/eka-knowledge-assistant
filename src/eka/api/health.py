"""Liveness and readiness probes.

Liveness reflects process health only. Readiness verifies critical dependencies
(the database) so orchestrators route traffic only when the service can serve it.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from eka.api.dependencies import get_session_factory

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def ready(
    response: Response,
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
) -> dict[str, str]:
    try:
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unavailable", "database": "down"}
    return {"status": "ok", "database": "up"}
