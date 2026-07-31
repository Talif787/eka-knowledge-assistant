"""End-to-end search: seed chunks, search, and confirm caching. Requires Postgres+pgvector."""
from __future__ import annotations

import uuid

import pytest

from eka.modules.ingestion.domain.chunk import Chunk
from eka.modules.ingestion.infrastructure.embedding import HashingEmbeddingModel
from eka.modules.ingestion.infrastructure.repository import SqlAlchemyChunkRepository
from eka.modules.retrieval.application.search import SearchHandler
from eka.modules.retrieval.domain.search import SearchQuery
from eka.modules.retrieval.infrastructure.memory_cache import InMemorySearchCache
from eka.modules.retrieval.infrastructure.pgvector_retriever import (
    PgVectorHybridRetriever,
)
from eka.modules.retrieval.infrastructure.reranker import LexicalReranker
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


async def test_search_returns_relevant_then_serves_from_cache(session_factory) -> None:
    tenant, collection = uuid.uuid4(), uuid.uuid4()
    d1, d2 = uuid.uuid4(), uuid.uuid4()
    await _seed(session_factory, tenant, collection, d1,
                "vector databases store embeddings for similarity search")
    await _seed(session_factory, tenant, collection, d2,
                "the museum opens at nine in the morning")

    cache = InMemorySearchCache()
    async with session_factory() as s:
        handler = SearchHandler(
            embedder=EMBEDDER,
            retriever=PgVectorHybridRetriever(s),
            reranker=LexicalReranker(),
            cache=cache,
            pool_size=10,
            cache_ttl_seconds=60,
        )
        query = SearchQuery(text="vector similarity search embeddings", top_k=3)
        first = await handler.handle(tenant, query)
        assert first
        assert first[0].document_id == d1
        second = await handler.handle(tenant, query)

    assert [c.chunk_id for c in second] == [c.chunk_id for c in first]  # cache hit
