"""Unit tests for the in-memory search cache (offline)."""

from __future__ import annotations

import asyncio
import uuid

from eka.modules.retrieval.domain.search import ScoredChunk
from eka.modules.retrieval.infrastructure.memory_cache import InMemorySearchCache


def _chunk() -> ScoredChunk:
    return ScoredChunk(uuid.uuid4(), uuid.uuid4(), "text", 0.5)


def test_miss_then_hit() -> None:
    async def scenario() -> None:
        cache = InMemorySearchCache()
        assert await cache.get("k") is None
        await cache.set("k", [_chunk()], 60)
        got = await cache.get("k")
        assert got is not None and len(got) == 1

    asyncio.run(scenario())


def test_expired_entry_is_a_miss() -> None:
    async def scenario() -> None:
        cache = InMemorySearchCache()
        await cache.set("k", [_chunk()], ttl_seconds=-1)
        assert await cache.get("k") is None

    asyncio.run(scenario())


def test_keys_are_isolated() -> None:
    async def scenario() -> None:
        cache = InMemorySearchCache()
        await cache.set("a", [_chunk()], 60)
        assert await cache.get("b") is None

    asyncio.run(scenario())
