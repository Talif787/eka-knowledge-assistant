"""Ingestion worker entry point.

Polls the database-backed queue, runs the ingestion pipeline for each claimed
job, and records success or failure. Jobs that exhaust their retries are moved to
the dead-letter state and their document is marked FAILED. Shuts down gracefully
on SIGINT and SIGTERM so in-flight jobs finish and locks are released.
"""
from __future__ import annotations

import asyncio
import contextlib
import signal

from sqlalchemy.ext.asyncio import AsyncEngine

from eka.config import Settings, get_settings
from eka.modules.documents.application.lifecycle import DocumentLifecycleService
from eka.modules.documents.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from eka.modules.ingestion.application.jobs import IngestionJob, JobQueue
from eka.modules.ingestion.application.pipeline import IngestDocumentHandler
from eka.modules.ingestion.domain.chunking import ChunkingConfig, RecursiveCharacterChunker
from eka.modules.ingestion.infrastructure.embedding import HashingEmbeddingModel
from eka.modules.ingestion.infrastructure.queue import SqlAlchemyJobQueue
from eka.modules.ingestion.infrastructure.unit_of_work import (
    SqlAlchemyIngestionUnitOfWork,
)
from eka.shared.infrastructure.database import create_engine, create_session_factory
from eka.shared.infrastructure.logging import configure_logging, get_logger
from eka.shared.infrastructure.observability import configure_tracing

logger = get_logger("worker")


class IngestionWorker:
    def __init__(
        self,
        *,
        queue: JobQueue,
        handler: IngestDocumentHandler,
        lifecycle: DocumentLifecycleService,
        worker_id: str,
        batch_size: int,
        poll_interval: float,
    ) -> None:
        self._queue = queue
        self._handler = handler
        self._lifecycle = lifecycle
        self._worker_id = worker_id
        self._batch_size = batch_size
        self._poll_interval = poll_interval
        self._stopping = asyncio.Event()

    def request_stop(self) -> None:
        self._stopping.set()

    async def run(self) -> None:
        logger.info("worker_started", worker_id=self._worker_id)
        while not self._stopping.is_set():
            processed = await self._drain_once()
            if processed == 0:
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(
                        self._stopping.wait(), timeout=self._poll_interval
                    )
        logger.info("worker_stopped", worker_id=self._worker_id)

    async def _drain_once(self) -> int:
        jobs = await self._queue.dequeue(self._worker_id, self._batch_size)
        for job in jobs:
            await self._process(job)
        return len(jobs)

    async def _process(self, job: IngestionJob) -> None:
        try:
            await self._handler.handle(job)
            await self._queue.complete(job)
        except Exception as exc:  # noqa: BLE001  (worker boundary: never crash the loop)
            dead_lettered = await self._queue.fail(job, repr(exc))
            logger.error(
                "job_failed",
                document_id=str(job.document_id),
                attempt=job.attempts + 1,
                dead_lettered=dead_lettered,
                error=str(exc),
            )
            if dead_lettered:
                try:
                    await self._lifecycle.mark_failed(job.tenant_id, job.document_id)
                except Exception:  # noqa: BLE001
                    logger.error("mark_failed_failed", document_id=str(job.document_id))


def build_worker(settings: Settings) -> tuple[IngestionWorker, AsyncEngine]:
    engine = create_engine(settings.database_dsn, pool_size=settings.database_pool_size)
    session_factory = create_session_factory(engine)

    queue = SqlAlchemyJobQueue(session_factory)
    lifecycle = DocumentLifecycleService(SqlAlchemyUnitOfWork(session_factory))
    handler = IngestDocumentHandler(
        uow_factory=lambda: SqlAlchemyIngestionUnitOfWork(session_factory),
        lifecycle=lifecycle,
        chunker=RecursiveCharacterChunker(
            ChunkingConfig(settings.chunk_size, settings.chunk_overlap)
        ),
        embedder=HashingEmbeddingModel(settings.embedding_dimension),
    )
    worker = IngestionWorker(
        queue=queue,
        handler=handler,
        lifecycle=lifecycle,
        worker_id=settings.worker_id,
        batch_size=settings.worker_batch_size,
        poll_interval=settings.worker_poll_interval_seconds,
    )
    return worker, engine


async def _main() -> None:
    settings = get_settings()
    configure_logging(level=settings.log_level, json_logs=settings.json_logs)
    configure_tracing(
        service_name=f"{settings.service_name}-worker", otlp_endpoint=settings.otlp_endpoint
    )
    worker, engine = build_worker(settings)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, worker.request_stop)

    try:
        await worker.run()
    finally:
        await engine.dispose()


def run() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    run()
