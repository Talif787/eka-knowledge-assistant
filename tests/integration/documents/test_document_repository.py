"""Integration tests for the SQLAlchemy document repository.

Requires a live Postgres. Run with:
    EKA_TEST_DATABASE_DSN=postgresql+asyncpg://eka:eka@localhost:5432/eka_test pytest
"""
from __future__ import annotations

import uuid

import pytest

from eka.modules.documents.domain.document import (
    ContentHash,
    Document,
    SourceType,
    Title,
)
from eka.modules.documents.infrastructure.repository import SqlAlchemyDocumentRepository
from eka.shared.domain.pagination import PageRequest
from tests.conftest import requires_db

pytestmark = [pytest.mark.asyncio, requires_db]


def _doc(tenant: uuid.UUID, content_hash: str) -> Document:
    return Document.register(
        tenant_id=tenant,
        collection_id=uuid.uuid4(),
        title=Title("Doc"),
        source_type=SourceType.UPLOAD,
        source_uri="s3://b/k",
        content_hash=ContentHash(content_hash),
    )


async def test_add_and_get_roundtrip(session_factory) -> None:
    tenant = uuid.uuid4()
    doc = _doc(tenant, "c" * 64)
    async with session_factory() as session:
        repo = SqlAlchemyDocumentRepository(session)
        await repo.add(doc)
        await session.commit()

    async with session_factory() as session:
        repo = SqlAlchemyDocumentRepository(session)
        loaded = await repo.get(tenant, doc.id)
    assert loaded is not None
    assert loaded.content_hash.value == "c" * 64


async def test_find_by_content_hash_supports_idempotency(session_factory) -> None:
    tenant = uuid.uuid4()
    doc = _doc(tenant, "d" * 64)
    async with session_factory() as session:
        repo = SqlAlchemyDocumentRepository(session)
        await repo.add(doc)
        await session.commit()

    async with session_factory() as session:
        repo = SqlAlchemyDocumentRepository(session)
        found = await repo.find_by_content_hash(tenant, ContentHash("d" * 64))
    assert found is not None and found.id == doc.id


async def test_list_is_tenant_scoped(session_factory) -> None:
    tenant_a, tenant_b = uuid.uuid4(), uuid.uuid4()
    async with session_factory() as session:
        repo = SqlAlchemyDocumentRepository(session)
        await repo.add(_doc(tenant_a, "e" * 64))
        await repo.add(_doc(tenant_b, "f" * 64))
        await session.commit()

    async with session_factory() as session:
        repo = SqlAlchemyDocumentRepository(session)
        page = await repo.list(tenant_a, PageRequest())
    assert page.total == 1
