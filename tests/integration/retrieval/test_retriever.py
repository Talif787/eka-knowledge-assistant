"""Integration tests for the hybrid pgvector retriever. Requires Postgres+pgvector."""
from __future__ import annotations

import uuid

import pytest

from eka.modules.ingestion.domain.chunk import Chunk
from eka.modules.ingestion.infrastructure.embedding import HashingEmbeddingModel
from eka.modules.ingestion.infrastructure.repository import SqlAlchemyChunkRepository
from eka.modules.retrieval.domain.search import SearchQuery
from eka.modules.retrieval.infrastructure.pgvector_retriever import (
    PgVectorHybridRetriever,
)
from tests.conftest import requires_db

pytestmark = [pytest.mark.asyncio, requires_db]

EMBEDDER = HashingEmbeddingModel(dimension=384)


async def _seed(session_factory, tenant, collection, document_id, chunk_text) -> None:
    embedding = (await EMBEDDER.embed([chunk_text]))[0]
    chunk = Chunk.create(
        tenant_id=tenant, document_id=document_id, collection_id=collection,
        document_version=1, ordinal=0, text=chunk_text, embedding=embedding,
    )
    async with session_factory() as s:
        await SqlAlchemyChunkRepository(s).replace_for_document(tenant, document_id, [chunk])
        await s.commit()


async def test_retrieves_relevant_and_scopes_by_tenant(session_factory) -> None:
    tenant, other, collection = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    d1, d2 = uuid.uuid4(), uuid.uuid4()
    db_text = "database indexing and query optimization"
    await _seed(session_factory, tenant, collection, d1, db_text)
    await _seed(session_factory, tenant, collection, d2, "sunny weather at the beach")
    await _seed(session_factory, other, collection, uuid.uuid4(), db_text)

    query = SearchQuery(text="database query optimization", top_k=5)
    query_embedding = (await EMBEDDER.embed([query.text]))[0]
    async with session_factory() as s:
        results = await PgVectorHybridRetriever(s).retrieve(tenant, query, query_embedding, 10)

    assert results
    assert all(r.document_id in (d1, d2) for r in results)  # tenant isolation
    assert results[0].document_id == d1  # relevant chunk ranks first


async def test_collection_filter_narrows_results(session_factory) -> None:
    tenant, wanted, other = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    d_wanted, d_other = uuid.uuid4(), uuid.uuid4()
    kafka_text = "kafka partitions and consumer groups"
    await _seed(session_factory, tenant, wanted, d_wanted, kafka_text)
    await _seed(session_factory, tenant, other, d_other, kafka_text)

    query = SearchQuery(text="kafka partitions", top_k=5, collection_id=wanted)
    query_embedding = (await EMBEDDER.embed([query.text]))[0]
    async with session_factory() as s:
        results = await PgVectorHybridRetriever(s).retrieve(tenant, query, query_embedding, 10)

    assert results
    assert all(r.document_id == d_wanted for r in results)
