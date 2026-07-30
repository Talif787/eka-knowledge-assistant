"""Ingestion DTOs."""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from eka.modules.ingestion.domain.chunk import Chunk


@dataclass(frozen=True, slots=True)
class ChunkDTO:
    id: uuid.UUID
    document_id: uuid.UUID
    ordinal: int
    text: str
    dimension: int

    @classmethod
    def from_entity(cls, chunk: Chunk) -> "ChunkDTO":
        return cls(
            id=chunk.id,
            document_id=chunk.document_id,
            ordinal=chunk.ordinal,
            text=chunk.text.value,
            dimension=chunk.embedding.dimension,
        )


@dataclass(frozen=True, slots=True)
class JobDTO:
    id: uuid.UUID
    document_id: uuid.UUID
    status: str
    attempts: int
    max_attempts: int
    last_error: str | None
