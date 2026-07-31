"""Retrieval value objects and ports.

A search runs two arms (dense vector and sparse keyword), fuses them, reranks the
fused candidates, and returns scored chunks with enough provenance to cite. The
Retriever, Reranker, and SearchCache ports keep those responsibilities swappable.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from eka.modules.ingestion.domain.embedding import Embedding
from eka.shared.domain.errors import ValidationError

MAX_TOP_K = 50


@dataclass(frozen=True, slots=True)
class SearchQuery:
    text: str
    top_k: int = 5
    collection_id: uuid.UUID | None = None

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValidationError("query text must not be empty")
        if self.top_k < 1 or self.top_k > MAX_TOP_K:
            raise ValidationError(f"top_k must be between 1 and {MAX_TOP_K}")


@dataclass(frozen=True, slots=True)
class ScoredChunk:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    text: str
    score: float


@runtime_checkable
class Retriever(Protocol):
    async def retrieve(
        self,
        tenant_id: uuid.UUID,
        query: SearchQuery,
        query_embedding: Embedding,
        pool_size: int,
    ) -> list[ScoredChunk]:
        """Return fused candidates (before reranking) for the query."""


@runtime_checkable
class Reranker(Protocol):
    async def rerank(
        self, query_text: str, candidates: list[ScoredChunk], top_k: int
    ) -> list[ScoredChunk]: ...


@runtime_checkable
class SearchCache(Protocol):
    async def get(self, key: str) -> list[ScoredChunk] | None: ...

    async def set(self, key: str, results: list[ScoredChunk], ttl_seconds: int) -> None: ...
