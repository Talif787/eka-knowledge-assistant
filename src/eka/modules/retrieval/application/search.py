"""Search use case: cache, embed, retrieve, rerank.

The query is embedded with the same model used at ingestion, so query and index
vectors share a space. Results are cached under an ACL-aware key; a cache failure
degrades to a live search rather than an error.
"""

from __future__ import annotations

import time
import uuid

from eka.modules.ingestion.domain.embedding import EmbeddingModel
from eka.modules.retrieval.application.cache_key import build_cache_key
from eka.modules.retrieval.domain.search import (
    Reranker,
    Retriever,
    ScoredChunk,
    SearchCache,
    SearchQuery,
)
from eka.shared.infrastructure.logging import get_logger
from eka.shared.infrastructure.metrics import record_search

logger = get_logger(__name__)


class SearchHandler:
    def __init__(
        self,
        *,
        embedder: EmbeddingModel,
        retriever: Retriever,
        reranker: Reranker,
        cache: SearchCache,
        pool_size: int = 50,
        cache_ttl_seconds: int = 300,
    ) -> None:
        self._embedder = embedder
        self._retriever = retriever
        self._reranker = reranker
        self._cache = cache
        self._pool_size = pool_size
        self._cache_ttl_seconds = cache_ttl_seconds

    async def handle(self, tenant_id: uuid.UUID, query: SearchQuery) -> list[ScoredChunk]:
        start = time.perf_counter()
        key = build_cache_key(tenant_id, query.collection_id, query.text, query.top_k)
        cached = await self._cache.get(key)
        if cached is not None:
            duration_ms = (time.perf_counter() - start) * 1000
            record_search(duration_ms=duration_ms, cache_hit=True)
            logger.info(
                "search_cache_hit",
                tenant_id=str(tenant_id),
                results=len(cached),
                duration_ms=round(duration_ms, 2),
            )
            return cached

        embedding = (await self._embedder.embed([query.text]))[0]
        candidates = await self._retriever.retrieve(
            tenant_id, query, embedding, self._pool_size
        )
        ranked = await self._reranker.rerank(query.text, candidates, query.top_k)
        await self._cache.set(key, ranked, self._cache_ttl_seconds)
        duration_ms = (time.perf_counter() - start) * 1000
        record_search(duration_ms=duration_ms, cache_hit=False)
        logger.info(
            "search_completed",
            tenant_id=str(tenant_id),
            results=len(ranked),
            duration_ms=round(duration_ms, 2),
        )
        return ranked
