"""Unit tests for the in-memory searcher (offline)."""

from __future__ import annotations

import asyncio
import uuid

from eka.modules.evaluation.domain.dataset import CorpusDoc
from eka.modules.evaluation.infrastructure.in_memory_searcher import InMemorySearcher
from eka.modules.ingestion.infrastructure.embedding import HashingEmbeddingModel
from eka.modules.retrieval.domain.search import ScoredChunk, SearchQuery
from eka.modules.retrieval.infrastructure.reranker import LexicalReranker


def test_retrieves_relevant_doc_first() -> None:
    corpus = [
        CorpusDoc("db", "databases organize information for efficient queries"),
        CorpusDoc("weather", "a cold front brings rain along the coast"),
        CorpusDoc("music", "the orchestra performed a symphony tonight"),
    ]
    searcher = InMemorySearcher(
        HashingEmbeddingModel(dimension=384), LexicalReranker(), corpus
    )

    async def run() -> list[ScoredChunk]:
        query = SearchQuery(text="how do databases handle queries", top_k=2)
        return await searcher.handle(uuid.uuid4(), query)

    results = asyncio.run(run())
    assert results
    assert "databases" in results[0].text
