"""Database-backed job queue.

A single-Postgres queue is the right MVP choice: it is transactional with the
domain writes, needs no extra infrastructure, and scales to meaningful throughput
using SELECT ... FOR UPDATE SKIP LOCKED for safe concurrent consumers. The
JobQueue port lets this be swapped for SQS or Kafka at scale without touching the
pipeline. Enqueue is idempotent per (document_id, version); jobs that exhaust
their retries move to a dead-letter state.
"""
from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from eka.modules.ingestion.application.jobs import (
    IngestionJob,
    JobStatus,
    compute_backoff_seconds,
)
from eka.modules.ingestion.infrastructure.models import IngestionJobModel
from eka.shared.domain.base import new_uuid, utcnow


class SqlAlchemyJobQueue:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def enqueue(
        self,
        tenant_id: uuid.UUID,
        document_id: uuid.UUID,
        collection_id: uuid.UUID,
        document_version: int,
        max_attempts: int = 5,
    ) -> None:
        now = utcnow()
        stmt = (
            pg_insert(IngestionJobModel)
            .values(
                id=new_uuid(),
                tenant_id=tenant_id,
                document_id=document_id,
                collection_id=collection_id,
                document_version=document_version,
                status=JobStatus.PENDING.value,
                attempts=0,
                max_attempts=max_attempts,
                available_at=now,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_nothing(
                index_elements=[
                    IngestionJobModel.document_id,
                    IngestionJobModel.document_version,
                ]
            )
        )
        async with self._session_factory() as session:
            await session.execute(stmt)
            await session.commit()

    async def dequeue(self, worker_id: str, batch_size: int = 1) -> list[IngestionJob]:
        now = utcnow()
        async with self._session_factory() as session:
            rows = (
                await session.execute(
                    select(IngestionJobModel)
                    .where(
                        IngestionJobModel.status == JobStatus.PENDING.value,
                        IngestionJobModel.available_at <= now,
                    )
                    .order_by(IngestionJobModel.available_at)
                    .limit(batch_size)
                    .with_for_update(skip_locked=True)
                )
            ).scalars().all()

            jobs: list[IngestionJob] = []
            for row in rows:
                row.status = JobStatus.PROCESSING.value
                row.locked_at = now
                row.locked_by = worker_id
                row.updated_at = now
                jobs.append(
                    IngestionJob(
                        id=row.id,
                        tenant_id=row.tenant_id,
                        document_id=row.document_id,
                        collection_id=row.collection_id,
                        document_version=row.document_version,
                        attempts=row.attempts,
                        max_attempts=row.max_attempts,
                    )
                )
            await session.commit()
            return jobs

    async def complete(self, job: IngestionJob) -> None:
        async with self._session_factory() as session:
            await session.execute(
                update(IngestionJobModel)
                .where(IngestionJobModel.id == job.id)
                .values(
                    status=JobStatus.COMPLETED.value,
                    locked_at=None,
                    locked_by=None,
                    updated_at=utcnow(),
                )
            )
            await session.commit()

    async def fail(self, job: IngestionJob, error: str) -> bool:
        attempts = job.attempts + 1
        dead_lettered = attempts >= job.max_attempts
        now = utcnow()
        if dead_lettered:
            values = {
                "status": JobStatus.DEAD_LETTER.value,
                "attempts": attempts,
                "last_error": error[:2000],
                "locked_at": None,
                "locked_by": None,
                "updated_at": now,
            }
        else:
            values = {
                "status": JobStatus.PENDING.value,
                "attempts": attempts,
                "available_at": now + timedelta(seconds=compute_backoff_seconds(attempts)),
                "last_error": error[:2000],
                "locked_at": None,
                "locked_by": None,
                "updated_at": now,
            }
        async with self._session_factory() as session:
            await session.execute(
                update(IngestionJobModel)
                .where(IngestionJobModel.id == job.id)
                .values(**values)
            )
            await session.commit()
        return dead_lettered
