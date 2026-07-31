"""Transport schemas for the search API."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field

from eka.modules.retrieval.application.dto import SearchResultDTO


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1)
    collection_id: uuid.UUID | None = None
    top_k: int = Field(default=5, ge=1, le=50)


class SearchResultItem(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    text: str
    score: float

    @classmethod
    def from_dto(cls, dto: SearchResultDTO) -> SearchResultItem:
        return cls(
            chunk_id=dto.chunk_id,
            document_id=dto.document_id,
            text=dto.text,
            score=dto.score,
        )


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]
