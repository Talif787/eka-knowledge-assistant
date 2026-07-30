"""Upload-content use case: the ingestion trigger.

Verifies the uploaded text against the content hash registered in Phase 1 (an
integrity check), stores it, and enqueues an ingestion job. Enqueue is idempotent,
so a repeated upload of the same version does not create duplicate work.
"""
from __future__ import annotations

import hashlib
import uuid
from collections.abc import Callable

from eka.modules.documents.application.queries import GetDocumentHandler, GetDocumentQuery
from eka.modules.ingestion.application.jobs import JobQueue
from eka.modules.ingestion.application.ports import IngestionUnitOfWork
from eka.shared.domain.errors import ValidationError


class UploadDocumentContentHandler:
    def __init__(
        self,
        *,
        get_document: GetDocumentHandler,
        uow_factory: Callable[[], IngestionUnitOfWork],
        queue: JobQueue,
        max_attempts: int = 5,
    ) -> None:
        self._get_document = get_document
        self._uow_factory = uow_factory
        self._queue = queue
        self._max_attempts = max_attempts

    async def handle(
        self, tenant_id: uuid.UUID, document_id: uuid.UUID, content: str
    ) -> None:
        document = await self._get_document.handle(
            GetDocumentQuery(tenant_id=tenant_id, document_id=document_id)
        )
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if digest != document.content_hash:
            raise ValidationError("content does not match the registered content_hash")

        async with self._uow_factory() as uow:
            await uow.content.put(tenant_id, document_id, content)
            await uow.commit()

        await self._queue.enqueue(
            tenant_id=tenant_id,
            document_id=document_id,
            collection_id=document.collection_id,
            document_version=document.version,
            max_attempts=self._max_attempts,
        )
