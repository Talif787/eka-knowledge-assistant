"""Integration: answers grounded in real retrieved chunks. Requires Postgres+pgvector."""
from __future__ import annotations

import uuid

import pytest

from eka.modules.generation.application.generate import GenerateAnswerHandler
from eka.modules.generation.domain.answer import EventType
from eka.modules.generation.domain.guardrails import PromptInjectionGuard
from eka.modules.generation.infrastructure.local_llm import LocalTemplateLanguageModel
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


async def _seed(session_factory, tenant, collection, document_id, text) -> None:
    embedding = (await EMBEDDER.embed([text]))[0]
    chunk = Chunk.create(
        tenant_id=tenant, document_id=document_id, collection_id=collection,
        document_version=1, ordinal=0, text=text, embedding=embedding,
    )
    async with session_factory() as s:
        await SqlAlchemyChunkRepository(s).replace_for_document(tenant, document_id, [chunk])
        await s.commit()


async def test_answer_grounds_in_retrieved_chunks(session_factory) -> None:
    tenant, collection = uuid.uuid4(), uuid.uuid4()
    d1 = uuid.uuid4()
    await _seed(
        session_factory, tenant, collection, d1,
        "Databases organize information so it can be queried efficiently.",
    )
    async with session_factory() as s:
        search = SearchHandler(
            embedder=EMBEDDER,
            retriever=PgVectorHybridRetriever(s),
            reranker=LexicalReranker(),
            cache=InMemorySearchCache(),
            pool_size=10,
            cache_ttl_seconds=60,
        )
        handler = GenerateAnswerHandler(
            searcher=search,
            guard=PromptInjectionGuard(),
            language_model=LocalTemplateLanguageModel(),
        )
        query = SearchQuery(text="how do databases query information", top_k=5)
        events = [e async for e in handler.stream(tenant, query)]

    assert events[0]["type"] == EventType.SOURCES
    assert events[-1]["type"] == EventType.DONE
    citations = events[0]["citations"]
    assert citations and citations[0]["document_id"] == str(d1)
    answer = "".join(str(e["text"]) for e in events if e["type"] == EventType.TOKEN)
    assert "Databases organize" in answer
