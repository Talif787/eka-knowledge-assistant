"""Ports the ingestion pipeline depends on (implemented by infrastructure)."""
from __future__ import annotations

import uuid
from types import TracebackType
from typing import Protocol, runtime_checkable

from eka.modules.ingestion.domain.chunk import Chunk


@runtime_checkable
class ChunkRepository(Protocol):
    async def replace_for_document(
        self, tenant_id: uuid.UUID, document_id: uuid.UUID, chunks: list[Chunk]
    ) -> None:
        """Idempotently replace all chunks for a document (delete then insert)."""

    async def delete_for_document(
        self, tenant_id: uuid.UUID, document_id: uuid.UUID
    ) -> None: ...

    async def list_for_document(
        self, tenant_id: uuid.UUID, document_id: uuid.UUID
    ) -> list[Chunk]: ...


@runtime_checkable
class ContentStore(Protocol):
    """Stand-in for object storage. Holds the raw extracted text of a document."""

    async def put(self, tenant_id: uuid.UUID, document_id: uuid.UUID, text: str) -> None: ...

    async def get(self, tenant_id: uuid.UUID, document_id: uuid.UUID) -> str | None: ...


@runtime_checkable
class IngestionUnitOfWork(Protocol):
    chunks: ChunkRepository
    content: ContentStore

    async def __aenter__(self) -> IngestionUnitOfWork: ...
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
