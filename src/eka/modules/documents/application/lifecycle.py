"""Document lifecycle service.

The ingestion context must transition a document through its lifecycle without
reaching into the Documents tables directly. It depends on this narrow service,
so data ownership stays with the Documents context.
"""
from __future__ import annotations

import uuid

from eka.shared.application.unit_of_work import UnitOfWork
from eka.shared.domain.errors import NotFoundError


class DocumentLifecycleService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def _transition(self, tenant_id: uuid.UUID, document_id: uuid.UUID, action: str) -> None:
        async with self._uow:
            document = await self._uow.documents.get(tenant_id, document_id)
            if document is None:
                raise NotFoundError("document not found")
            getattr(document, action)()
            await self._uow.documents.save(document)
            await self._uow.commit()

    async def mark_ingesting(self, tenant_id: uuid.UUID, document_id: uuid.UUID) -> None:
        await self._transition(tenant_id, document_id, "mark_ingesting")

    async def mark_indexed(self, tenant_id: uuid.UUID, document_id: uuid.UUID) -> None:
        await self._transition(tenant_id, document_id, "mark_indexed")

    async def mark_failed(self, tenant_id: uuid.UUID, document_id: uuid.UUID) -> None:
        await self._transition(tenant_id, document_id, "mark_failed")
