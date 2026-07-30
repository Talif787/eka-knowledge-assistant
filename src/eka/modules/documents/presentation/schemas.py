"""Transport schemas for the Documents API (Pydantic v2)."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from eka.modules.documents.application.dto import DocumentDTO


class RegisterDocumentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    collection_id: uuid.UUID
    title: str = Field(min_length=1, max_length=512)
    source_type: str
    source_uri: str = Field(min_length=1, max_length=2048)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class DocumentResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    collection_id: uuid.UUID
    title: str
    source_type: str
    source_uri: str
    content_hash: str
    status: str
    version: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_dto(cls, dto: DocumentDTO) -> "DocumentResponse":
        return cls(
            id=dto.id,
            tenant_id=dto.tenant_id,
            collection_id=dto.collection_id,
            title=dto.title,
            source_type=dto.source_type,
            source_uri=dto.source_uri,
            content_hash=dto.content_hash,
            status=dto.status,
            version=dto.version,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
        )


class PageMeta(BaseModel):
    total: int
    limit: int
    offset: int
    has_more: bool


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    meta: PageMeta
