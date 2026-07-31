"""Local lexical reranker.

A deterministic, dependency-free reranker for development and tests. It reorders
fused candidates by combining the (normalized) retrieval score with query-term
coverage and an exact-phrase bonus. A cross-encoder model implements the same
Reranker port in production.
"""
from __future__ import annotations

import re

from eka.modules.retrieval.domain.search import ScoredChunk

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_W_RETRIEVAL = 0.3
_W_COVERAGE = 0.6
_W_PHRASE = 0.1


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


class LexicalReranker:
    async def rerank(
        self, query_text: str, candidates: list[ScoredChunk], top_k: int
    ) -> list[ScoredChunk]:
        if not candidates:
            return []

        query_tokens = _tokens(query_text)
        normalized_query = " ".join(query_text.lower().split())
        scores = [c.score for c in candidates]
        low, high = min(scores), max(scores)
        span = high - low

        reranked: list[ScoredChunk] = []
        for candidate in candidates:
            base = (candidate.score - low) / span if span else 0.0
            chunk_tokens = _tokens(candidate.text)
            coverage = (
                len(query_tokens & chunk_tokens) / len(query_tokens)
                if query_tokens
                else 0.0
            )
            phrase = 1.0 if normalized_query in candidate.text.lower() else 0.0
            final = _W_RETRIEVAL * base + _W_COVERAGE * coverage + _W_PHRASE * phrase
            reranked.append(
                ScoredChunk(
                    chunk_id=candidate.chunk_id,
                    document_id=candidate.document_id,
                    text=candidate.text,
                    score=final,
                )
            )

        reranked.sort(key=lambda c: c.score, reverse=True)
        return reranked[:top_k]
