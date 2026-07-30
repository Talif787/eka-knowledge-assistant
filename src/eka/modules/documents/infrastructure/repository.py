"""SQLAlchemy adapter implementing the DocumentRepository port."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from eka.modules.documents.domain.document import (
    ContentHash,
    Document,
    DocumentStatus,
    SourceType,
    Title,
)
from eka.modules.documents.infrastructure.models import DocumentModel
from eka.shared.domain.pagination import Page, PageRequest, SortDirection

_SORTABLE = {"created_at", "updated_at", "title", "status"}


def _to_domain(model: DocumentModel) -> Document:
    return Document(
        id=model.id,
        tenant_id=model.tenant_id,
        collection_id=model.collection_id,
        title=Title(model.title),
        source_type=SourceType(model.source_type),
        source_uri=model.source_uri,
        content_hash=ContentHash(model.content_hash),
        status=DocumentStatus(model.status),
        version=model.version,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _apply(model: DocumentModel, doc: Document) -> None:
    model.tenant_id = doc.tenant_id
    model.collection_id = doc.collection_id
    model.title = doc.title.value
    model.source_type = doc.source_type.value
    model.source_uri = doc.source_uri
    model.content_hash = doc.content_hash.value
    model.status = doc.status.value
    model.version = doc.version
    model.created_at = doc.created_at
    model.updated_at = doc.updated_at


class SqlAlchemyDocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, document: Document) -> None:
        model = DocumentModel(id=document.id)
        _apply(model, document)
        self._session.add(model)

    async def save(self, document: Document) -> None:
        model = await self._session.get(DocumentModel, document.id)
        if model is None:
            model = DocumentModel(id=document.id)
            self._session.add(model)
        _apply(model, document)

    async def get(self, tenant_id: uuid.UUID, document_id: uuid.UUID) -> Document | None:
        stmt = select(DocumentModel).where(
            DocumentModel.id == document_id,
            DocumentModel.tenant_id == tenant_id,
            DocumentModel.status != DocumentStatus.DELETED.value,
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_domain(model) if model else None

    async def find_by_content_hash(
        self, tenant_id: uuid.UUID, content_hash: ContentHash
    ) -> Document | None:
        stmt = select(DocumentModel).where(
            DocumentModel.tenant_id == tenant_id,
            DocumentModel.content_hash == content_hash.value,
            DocumentModel.status != DocumentStatus.DELETED.value,
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_domain(model) if model else None

    async def list(
        self,
        tenant_id: uuid.UUID,
        page: PageRequest,
        collection_id: uuid.UUID | None = None,
    ) -> Page[Document]:
        conditions = [
            DocumentModel.tenant_id == tenant_id,
            DocumentModel.status != DocumentStatus.DELETED.value,
        ]
        if collection_id is not None:
            conditions.append(DocumentModel.collection_id == collection_id)

        total = (
            await self._session.execute(
                select(func.count()).select_from(DocumentModel).where(*conditions)
            )
        ).scalar_one()

        sort_field = "created_at"
        direction = SortDirection.DESC
        if page.sort and page.sort.field in _SORTABLE:
            sort_field = page.sort.field
            direction = page.sort.direction
        column = getattr(DocumentModel, sort_field)
        order = column.asc() if direction is SortDirection.ASC else column.desc()

        stmt = (
            select(DocumentModel)
            .where(*conditions)
            .order_by(order)
            .limit(page.limit)
            .offset(page.offset)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return Page(
            items=[_to_domain(r) for r in rows],
            total=int(total),
            limit=page.limit,
            offset=page.offset,
        )
