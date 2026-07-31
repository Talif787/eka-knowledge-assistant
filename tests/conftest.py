"""Shared pytest fixtures.

The database fixtures target a disposable Postgres (see docker-compose). They are
skipped automatically when EKA_TEST_DATABASE_DSN is not set, so unit tests always
run and integration tests run only where a database is available.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio

DSN = os.getenv("EKA_TEST_DATABASE_DSN")
requires_db = pytest.mark.skipif(DSN is None, reason="EKA_TEST_DATABASE_DSN not set")


@pytest_asyncio.fixture
async def session_factory() -> AsyncIterator:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from eka.shared.infrastructure.database import Base

    engine = create_async_engine(DSN)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()
