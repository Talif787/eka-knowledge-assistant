"""Write-side use cases (commands).

Handlers orchestrate the aggregate and the unit of work. Idempotency on
registration is enforced by content hash so retried ingestion does not create
duplicates.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from eka.modules.documents.application.dto import DocumentDTO
from eka.modules.documents.domain.document import (
    ContentHash,
    Document,
    SourceType,
    Title,
)
from eka.shared.application.unit_of_work import UnitOfWork
from eka.shared.domain.errors import NotFoundError


@dataclass(frozen=True, slots=True)
class RegisterDocumentCommand:
    tenant_id: uuid.UUID
    collection_id: uuid.UUID
    title: str
    source_type: str
    source_uri: str
    content_hash: str


class RegisterDocumentHandler:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def handle(self, command: RegisterDocumentCommand) -> DocumentDTO:
        content_hash = ContentHash(command.content_hash)
        async with self._uow:
            existing = await self._uow.documents.find_by_content_hash(
                command.tenant_id, content_hash
            )
            if existing is not None:
                return DocumentDTO.from_aggregate(existing)

            document = Document.register(
                tenant_id=command.tenant_id,
                collection_id=command.collection_id,
                title=Title(command.title),
                source_type=SourceType(command.source_type),
                source_uri=command.source_uri,
                content_hash=content_hash,
            )
            await self._uow.documents.add(document)
            await self._uow.commit()
            return DocumentDTO.from_aggregate(document)


@dataclass(frozen=True, slots=True)
class DeleteDocumentCommand:
    tenant_id: uuid.UUID
    document_id: uuid.UUID


class DeleteDocumentHandler:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def handle(self, command: DeleteDocumentCommand) -> None:
        async with self._uow:
            document = await self._uow.documents.get(command.tenant_id, command.document_id)
            if document is None:
                raise NotFoundError("document not found")
            document.delete()
            await self._uow.documents.save(document)
            await self._uow.commit()
