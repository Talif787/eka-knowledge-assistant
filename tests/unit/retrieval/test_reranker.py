"""Unit tests for the lexical reranker (offline)."""

from __future__ import annotations

import asyncio
import uuid

from eka.modules.retrieval.domain.search import ScoredChunk
from eka.modules.retrieval.infrastructure.reranker import LexicalReranker


def _rerank(query: str, candidates: list[ScoredChunk], top_k: int) -> list[ScoredChunk]:
    return asyncio.run(LexicalReranker().rerank(query, candidates, top_k))


def test_empty_candidates() -> None:
    assert _rerank("anything", [], 5) == []


def test_lexically_relevant_beats_high_score_irrelevant() -> None:
    d = uuid.uuid4()
    candidates = [
        ScoredChunk(uuid.uuid4(), d, "the weather is nice today", 0.9),
        ScoredChunk(uuid.uuid4(), d, "database indexing speeds up queries", 0.3),
    ]
    out = _rerank("database indexing queries", candidates, 2)
    assert "database" in out[0].text


def test_top_k_limits_results() -> None:
    d = uuid.uuid4()
    candidates = [ScoredChunk(uuid.uuid4(), d, f"chunk {i}", 0.5) for i in range(5)]
    assert len(_rerank("chunk", candidates, 2)) == 2


def test_exact_phrase_gets_a_bonus() -> None:
    d = uuid.uuid4()
    # both cover every query token; only the second contains the contiguous phrase
    candidates = [
        ScoredChunk(uuid.uuid4(), d, "topics and other index hnsw appear scrambled here", 0.5),
        ScoredChunk(uuid.uuid4(), d, "the hnsw index and other topics", 0.5),
    ]
    out = _rerank("hnsw index and other topics", candidates, 2)
    assert out[0].text == "the hnsw index and other topics"
