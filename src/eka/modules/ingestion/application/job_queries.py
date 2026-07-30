"""Read side for ingestion jobs (status and dead-letter inspection)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from eka.modules.ingestion.application.dto import JobDTO
from eka.modules.ingestion.infrastructure.models import IngestionJobModel
from eka.shared.domain.pagination import Page, PageRequest


@dataclass(frozen=True, slots=True)
class ListJobsQuery:
    tenant_id: uuid.UUID
    page: PageRequest
    status: str | None = None


class ListJobsHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: ListJobsQuery) -> Page[JobDTO]:
        conditions = [IngestionJobModel.tenant_id == query.tenant_id]
        if query.status:
            conditions.append(IngestionJobModel.status == query.status)
        rows = (
            await self._session.execute(
                select(IngestionJobModel)
                .where(*conditions)
                .order_by(IngestionJobModel.updated_at.desc())
                .limit(query.page.limit)
                .offset(query.page.offset)
            )
        ).scalars().all()
        items = [
            JobDTO(
                id=r.id,
                document_id=r.document_id,
                status=r.status,
                attempts=r.attempts,
                max_attempts=r.max_attempts,
                last_error=r.last_error,
            )
            for r in rows
        ]
        return Page(
            items=items,
            total=len(items),
            limit=query.page.limit,
            offset=query.page.offset,
        )
