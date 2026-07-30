"""Read-side use cases (queries).

Kept separate from commands so read and write paths can be optimized and scaled
independently as the system grows (CQRS applied where it pays).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from eka.modules.documents.application.dto import DocumentDTO
from eka.modules.documents.domain.repository import DocumentRepository
from eka.shared.domain.errors import NotFoundError
from eka.shared.domain.pagination import Page, PageRequest


@dataclass(frozen=True, slots=True)
class GetDocumentQuery:
    tenant_id: uuid.UUID
    document_id: uuid.UUID


class GetDocumentHandler:
    def __init__(self, repository: DocumentRepository) -> None:
        self._repository = repository

    async def handle(self, query: GetDocumentQuery) -> DocumentDTO:
        document = await self._repository.get(query.tenant_id, query.document_id)
        if document is None:
            raise NotFoundError("document not found")
        return DocumentDTO.from_aggregate(document)


@dataclass(frozen=True, slots=True)
class ListDocumentsQuery:
    tenant_id: uuid.UUID
    page: PageRequest
    collection_id: uuid.UUID | None = None


class ListDocumentsHandler:
    def __init__(self, repository: DocumentRepository) -> None:
        self._repository = repository

    async def handle(self, query: ListDocumentsQuery) -> Page[DocumentDTO]:
        page = await self._repository.list(
            query.tenant_id, query.page, query.collection_id
        )
        return Page(
            items=[DocumentDTO.from_aggregate(d) for d in page.items],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        )
