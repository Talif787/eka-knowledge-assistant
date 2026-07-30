"""Transport schemas for the ingestion API."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field

from eka.modules.ingestion.application.dto import ChunkDTO, JobDTO


class UploadContentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1)


class ContentAcceptedResponse(BaseModel):
    document_id: uuid.UUID
    status: str = "queued"


class ChunkResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    ordinal: int
    text: str
    dimension: int

    @classmethod
    def from_dto(cls, dto: ChunkDTO) -> ChunkResponse:
        return cls(
            id=dto.id,
            document_id=dto.document_id,
            ordinal=dto.ordinal,
            text=dto.text,
            dimension=dto.dimension,
        )


class ChunkListResponse(BaseModel):
    items: list[ChunkResponse]
    count: int


class JobResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    status: str
    attempts: int
    max_attempts: int
    last_error: str | None

    @classmethod
    def from_dto(cls, dto: JobDTO) -> JobResponse:
        return cls(
            id=dto.id,
            document_id=dto.document_id,
            status=dto.status,
            attempts=dto.attempts,
            max_attempts=dto.max_attempts,
            last_error=dto.last_error,
        )


class JobListResponse(BaseModel):
    items: list[JobResponse]
