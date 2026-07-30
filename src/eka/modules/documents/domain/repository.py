"""Persistence port for the Documents context.

Defined in the domain so the direction of dependency points inward: the
infrastructure adapter implements this contract, not the other way around.
"""
from __future__ import annotations

import uuid
from typing import Protocol, runtime_checkable

from eka.modules.documents.domain.document import ContentHash, Document
from eka.shared.domain.pagination import Page, PageRequest


@runtime_checkable
class DocumentRepository(Protocol):
    async def add(self, document: Document) -> None: ...

    async def get(self, tenant_id: uuid.UUID, document_id: uuid.UUID) -> Document | None: ...

    async def find_by_content_hash(
        self, tenant_id: uuid.UUID, content_hash: ContentHash
    ) -> Document | None: ...

    async def list(
        self,
        tenant_id: uuid.UUID,
        page: PageRequest,
        collection_id: uuid.UUID | None = None,
    ) -> Page[Document]: ...

    async def save(self, document: Document) -> None: ...
