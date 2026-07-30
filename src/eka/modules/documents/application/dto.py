"""Application-layer data transfer objects.

DTOs decouple the transport/presentation contract from the domain aggregate so
the API can evolve independently of internal model changes.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from eka.modules.documents.domain.document import Document


@dataclass(frozen=True, slots=True)
class DocumentDTO:
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
    def from_aggregate(cls, doc: Document) -> DocumentDTO:
        return cls(
            id=doc.id,
            tenant_id=doc.tenant_id,
            collection_id=doc.collection_id,
            title=doc.title.value,
            source_type=doc.source_type.value,
            source_uri=doc.source_uri,
            content_hash=doc.content_hash.value,
            status=doc.status.value,
            version=doc.version,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )
