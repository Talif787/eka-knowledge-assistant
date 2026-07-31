"""Integration tests for the database-backed job queue.

Requires a live Postgres. Exercises idempotent enqueue, SKIP LOCKED dequeue,
completion, retry scheduling, and the dead-letter transition.
"""

from __future__ import annotations

import uuid

import pytest

from eka.modules.ingestion.infrastructure.queue import SqlAlchemyJobQueue
from tests.conftest import requires_db

pytestmark = [pytest.mark.asyncio, requires_db]


async def _enqueue(queue: SqlAlchemyJobQueue, tenant, doc, version=1, max_attempts=3):
    await queue.enqueue(
        tenant,
        doc,
        collection_id=uuid.uuid4(),
        document_version=version,
        max_attempts=max_attempts,
    )


async def test_enqueue_is_idempotent_per_version(session_factory) -> None:
    queue = SqlAlchemyJobQueue(session_factory)
    tenant, doc = uuid.uuid4(), uuid.uuid4()
    await _enqueue(queue, tenant, doc)
    await _enqueue(queue, tenant, doc)  # duplicate, ignored
    jobs = await queue.dequeue("w1", batch_size=10)
    assert len([j for j in jobs if j.document_id == doc]) == 1


async def test_dequeue_marks_processing_and_skips_claimed(session_factory) -> None:
    queue = SqlAlchemyJobQueue(session_factory)
    tenant = uuid.uuid4()
    await _enqueue(queue, tenant, uuid.uuid4())
    first = await queue.dequeue("w1", batch_size=10)
    second = await queue.dequeue("w2", batch_size=10)
    assert len(first) == 1
    assert second == []  # already claimed and now processing


async def test_complete_marks_completed(session_factory) -> None:
    queue = SqlAlchemyJobQueue(session_factory)
    tenant = uuid.uuid4()
    await _enqueue(queue, tenant, uuid.uuid4())
    (job,) = await queue.dequeue("w1")
    await queue.complete(job)
    assert await queue.dequeue("w1") == []


async def test_fail_retries_then_dead_letters(session_factory) -> None:
    queue = SqlAlchemyJobQueue(session_factory)
    tenant, doc = uuid.uuid4(), uuid.uuid4()
    await _enqueue(queue, tenant, doc, max_attempts=2)
    (job,) = await queue.dequeue("w1")
    dead = await queue.fail(job, "boom")
    assert dead is False  # first failure schedules a retry (in the future)
    # simulate the retry attempt reaching max
    from eka.modules.ingestion.application.jobs import IngestionJob

    retried = IngestionJob(
        id=job.id,
        tenant_id=job.tenant_id,
        document_id=job.document_id,
        collection_id=job.collection_id,
        document_version=job.document_version,
        attempts=1,
        max_attempts=2,
    )
    dead = await queue.fail(retried, "boom again")
    assert dead is True
