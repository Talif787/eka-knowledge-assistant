"""Embedding value object and the embedding-model port.

The domain expresses only what it needs: an immutable, dimensioned vector and an
interface for turning text into such vectors. Concrete models (a local model, or
a hosted provider) live in infrastructure so they stay swappable.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from eka.shared.domain.errors import ValidationError


@dataclass(frozen=True, slots=True)
class Embedding:
    values: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.values:
            raise ValidationError("embedding must not be empty")

    @property
    def dimension(self) -> int:
        return len(self.values)

    def cosine_similarity(self, other: Embedding) -> float:
        if self.dimension != other.dimension:
            raise ValidationError("cannot compare embeddings of different dimensions")
        dot = sum(a * b for a, b in zip(self.values, other.values, strict=True))
        norm = math.sqrt(sum(a * a for a in self.values)) * math.sqrt(
            sum(b * b for b in other.values)
        )
        return dot / norm if norm else 0.0


@runtime_checkable
class EmbeddingModel(Protocol):
    @property
    def dimension(self) -> int: ...

    async def embed(self, texts: list[str]) -> list[Embedding]: ...
