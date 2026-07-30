"""Deterministic local embedding model (feature hashing).

A real, dependency-free embedder for local development and tests: it maps token
frequencies into a fixed-dimension signed vector and L2-normalizes. It is
deterministic and gives higher cosine similarity to texts that share vocabulary,
which is enough to exercise the pipeline and, later, retrieval. A hosted semantic
model implements the same EmbeddingModel port for production.
"""
from __future__ import annotations

import hashlib
import math
import re

from eka.modules.ingestion.domain.embedding import Embedding, EmbeddingModel

_TOKEN_RE = re.compile(r"[a-z0-9]+")


class HashingEmbeddingModel(EmbeddingModel):
    def __init__(self, dimension: int = 384) -> None:
        if dimension <= 0:
            raise ValueError("dimension must be positive")
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed(self, texts: list[str]) -> list[Embedding]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> Embedding:
        vector = [0.0] * self._dimension
        for token in _TOKEN_RE.findall(text.lower()):
            digest = hashlib.sha1(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self._dimension
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(v * v for v in vector))
        if norm == 0.0:
            vector[0] = 1.0
            norm = 1.0
        return Embedding(tuple(v / norm for v in vector))
