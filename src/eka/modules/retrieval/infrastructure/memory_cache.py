"""In-memory search cache (tests and fallback). No third-party dependencies."""
from __future__ import annotations

import time

from eka.modules.retrieval.domain.search import ScoredChunk


class InMemorySearchCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[float, list[ScoredChunk]]] = {}

    async def get(self, key: str) -> list[ScoredChunk] | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, results = entry
        if expires_at < time.monotonic():
            del self._store[key]
            return None
        return list(results)

    async def set(self, key: str, results: list[ScoredChunk], ttl_seconds: int) -> None:
        self._store[key] = (time.monotonic() + ttl_seconds, list(results))
