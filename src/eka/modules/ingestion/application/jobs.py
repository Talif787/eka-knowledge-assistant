"""Ingestion job model, retry policy, and the queue port.

The queue is modeled as a port so the database-backed implementation used in the
monolith can be replaced by SQS or Kafka at scale without touching the pipeline.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable

_BASE_BACKOFF_SECONDS = 5
_MAX_BACKOFF_SECONDS = 3600


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    DEAD_LETTER = "dead_letter"


def compute_backoff_seconds(attempts: int) -> int:
    """Exponential backoff with a ceiling.

    Deterministic by design so the policy is testable. In production a small
    random jitter is layered on to avoid retry synchronization.
    """
    if attempts < 1:
        return 0
    delay = _BASE_BACKOFF_SECONDS * (2 ** (attempts - 1))
    return min(delay, _MAX_BACKOFF_SECONDS)


@dataclass(frozen=True, slots=True)
class IngestionJob:
    id: uuid.UUID
    tenant_id: uuid.UUID
    document_id: uuid.UUID
    collection_id: uuid.UUID
    document_version: int
    attempts: int
    max_attempts: int


@runtime_checkable
class JobQueue(Protocol):
    async def enqueue(
        self,
        tenant_id: uuid.UUID,
        document_id: uuid.UUID,
        collection_id: uuid.UUID,
        document_version: int,
        max_attempts: int = 5,
    ) -> None:
        """Enqueue an ingestion job. Idempotent per (document_id, version)."""

    async def dequeue(self, worker_id: str, batch_size: int = 1) -> list[IngestionJob]:
        """Atomically claim pending jobs using row-level locking."""

    async def complete(self, job: IngestionJob) -> None: ...

    async def fail(self, job: IngestionJob, error: str) -> bool:
        """Record a failure. Returns True when the job was moved to the DLQ."""
