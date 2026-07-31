"""Redis-backed search cache.

Treats any Redis failure as a cache miss so search stays available when the
cache does not. Entries use the ACL-aware key built upstream.
"""
from __future__ import annotations

import json
import uuid

from redis.asyncio import Redis
from redis.exceptions import RedisError

from eka.modules.retrieval.domain.search import ScoredChunk
from eka.shared.infrastructure.logging import get_logger

logger = get_logger(__name__)


def serialize(results: list[ScoredChunk]) -> str:
    return json.dumps(
        [
            {
                "chunk_id": str(c.chunk_id),
                "document_id": str(c.document_id),
                "text": c.text,
                "score": c.score,
            }
            for c in results
        ]
    )


def deserialize(payload: str | bytes) -> list[ScoredChunk]:
    items = json.loads(payload)
    return [
        ScoredChunk(
            chunk_id=uuid.UUID(item["chunk_id"]),
            document_id=uuid.UUID(item["document_id"]),
            text=item["text"],
            score=float(item["score"]),
        )
        for item in items
    ]


class RedisSearchCache:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def get(self, key: str) -> list[ScoredChunk] | None:
        try:
            raw = await self._redis.get(key)
        except RedisError:
            logger.warning("search_cache_unavailable", operation="get")
            return None
        if raw is None:
            return None
        return deserialize(raw)

    async def set(self, key: str, results: list[ScoredChunk], ttl_seconds: int) -> None:
        try:
            await self._redis.set(key, serialize(results), ex=ttl_seconds)
        except RedisError:
            logger.warning("search_cache_unavailable", operation="set")
