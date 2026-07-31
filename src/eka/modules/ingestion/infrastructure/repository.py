"""SQLAlchemy adapters for chunks and document content."""
from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from eka.modules.ingestion.domain.chunk import Chunk, ChunkText
from eka.modules.ingestion.domain.embedding import Embedding
from eka.modules.ingestion.infrastructure.models import ChunkModel, DocumentContentModel
from eka.shared.domain.base import utcnow


def _to_domain(model: ChunkModel) -> Chunk:
    return Chunk(
        id=model.id,
        tenant_id=model.tenant_id,
        document_id=model.document_id,
        collection_id=model.collection_id,
        document_version=model.document_version,
        ordinal=model.ordinal,
        text=ChunkText(model.text),
        embedding=Embedding(tuple(float(v) for v in model.embedding)),
    )


class SqlAlchemyChunkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def replace_for_document(
        self, tenant_id: uuid.UUID, document_id: uuid.UUID, chunks: list[Chunk]
    ) -> None:
        await self.delete_for_document(tenant_id, document_id)
        now = utcnow()
        self._session.add_all(
            ChunkModel(
                id=chunk.id,
                tenant_id=chunk.tenant_id,
                document_id=chunk.document_id,
                collection_id=chunk.collection_id,
                document_version=chunk.document_version,
                ordinal=chunk.ordinal,
                text=chunk.text.value,
                embedding=list(chunk.embedding.values),
                created_at=now,
            )
            for chunk in chunks
        )

    async def delete_for_document(
        self, tenant_id: uuid.UUID, document_id: uuid.UUID
    ) -> None:
        await self._session.execute(
            delete(ChunkModel).where(
                ChunkModel.tenant_id == tenant_id,
                ChunkModel.document_id == document_id,
            )
        )

    async def list_for_document(
        self, tenant_id: uuid.UUID, document_id: uuid.UUID
    ) -> list[Chunk]:
        rows = (
            await self._session.execute(
                select(ChunkModel)
                .where(
                    ChunkModel.tenant_id == tenant_id,
                    ChunkModel.document_id == document_id,
                )
                .order_by(ChunkModel.ordinal)
            )
        ).scalars().all()
        return [_to_domain(r) for r in rows]


class SqlAlchemyContentStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def put(self, tenant_id: uuid.UUID, document_id: uuid.UUID, text: str) -> None:
        now = utcnow()
        stmt = pg_insert(DocumentContentModel).values(
            document_id=document_id,
            tenant_id=tenant_id,
            text=text,
            created_at=now,
            updated_at=now,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[DocumentContentModel.document_id],
            set_={"text": text, "updated_at": now},
        )
        await self._session.execute(stmt)

    async def get(self, tenant_id: uuid.UUID, document_id: uuid.UUID) -> str | None:
        row = (
            await self._session.execute(
                select(DocumentContentModel.text).where(
                    DocumentContentModel.document_id == document_id,
                    DocumentContentModel.tenant_id == tenant_id,
                )
            )
        ).scalar_one_or_none()
        return row
