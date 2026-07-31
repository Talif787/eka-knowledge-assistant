"""Retrieval DTOs."""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from eka.modules.retrieval.domain.search import ScoredChunk


@dataclass(frozen=True, slots=True)
class SearchResultDTO:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    text: str
    score: float

    @classmethod
    def from_scored_chunk(cls, chunk: ScoredChunk) -> SearchResultDTO:
        return cls(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            text=chunk.text,
            score=chunk.score,
        )
