"""The ingestion pipeline (a saga): extract, chunk, embed, index.

Steps are ordered so a failure at any point leaves the system recoverable:
the document is marked INGESTING up front and INDEXED only on success; a job
that exhausts its retries marks the document FAILED. Re-running is safe because
chunk writes replace the prior set for the document (idempotent by design).
"""
from __future__ import annotations

from collections.abc import Callable

from eka.modules.documents.application.lifecycle import DocumentLifecycleService
from eka.modules.ingestion.application.jobs import IngestionJob
from eka.modules.ingestion.application.ports import IngestionUnitOfWork
from eka.modules.ingestion.domain.chunk import Chunk, Chunker
from eka.modules.ingestion.domain.embedding import EmbeddingModel
from eka.shared.domain.errors import DomainError
from eka.shared.infrastructure.logging import get_logger

logger = get_logger(__name__)


class ContentMissingError(DomainError):
    code = "content_missing"


class IngestDocumentHandler:
    def __init__(
        self,
        *,
        uow_factory: Callable[[], IngestionUnitOfWork],
        lifecycle: DocumentLifecycleService,
        chunker: Chunker,
        embedder: EmbeddingModel,
    ) -> None:
        self._uow_factory = uow_factory
        self._lifecycle = lifecycle
        self._chunker = chunker
        self._embedder = embedder

    async def handle(self, job: IngestionJob) -> None:
        log = logger.bind(document_id=str(job.document_id), attempt=job.attempts + 1)
        await self._lifecycle.mark_ingesting(job.tenant_id, job.document_id)

        async with self._uow_factory() as uow:
            text = await uow.content.get(job.tenant_id, job.document_id)
            if text is None:
                raise ContentMissingError("no stored content for document")

            pieces = self._chunker.split(text)
            if not pieces:
                await uow.chunks.replace_for_document(job.tenant_id, job.document_id, [])
                await uow.commit()
                await self._lifecycle.mark_indexed(job.tenant_id, job.document_id)
                log.info("ingestion_completed", chunks=0)
                return

            embeddings = await self._embedder.embed([p.text for p in pieces])
            chunks = [
                Chunk.create(
                    tenant_id=job.tenant_id,
                    document_id=job.document_id,
                    collection_id=job.collection_id,
                    document_version=job.document_version,
                    ordinal=piece.ordinal,
                    text=piece.text,
                    embedding=embedding,
                )
                for piece, embedding in zip(pieces, embeddings, strict=True)
            ]
            await uow.chunks.replace_for_document(job.tenant_id, job.document_id, chunks)
            await uow.commit()

        await self._lifecycle.mark_indexed(job.tenant_id, job.document_id)
        log.info("ingestion_completed", chunks=len(pieces))
