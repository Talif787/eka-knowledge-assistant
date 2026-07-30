"""Domain building blocks shared across bounded contexts.

Intentionally free of framework and I/O dependencies so the domain layer
remains pure and unit-testable without infrastructure.
"""
from __future__ import annotations

import uuid
from abc import ABC
from dataclasses import dataclass, field
from datetime import UTC, datetime


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_uuid() -> uuid.UUID:
    return uuid.uuid4()


@dataclass(frozen=True, slots=True)
class ValueObject:
    """Marker base for immutable, equality-by-value objects."""


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """Base type for facts that have happened within the domain."""

    event_id: uuid.UUID = field(default_factory=new_uuid, kw_only=True)
    occurred_at: datetime = field(default_factory=utcnow, kw_only=True)

    @property
    def name(self) -> str:
        return type(self).__name__


class Entity(ABC):
    """An object defined by identity rather than attributes."""

    id: uuid.UUID

    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and other.id == self.id

    def __hash__(self) -> int:
        return hash((type(self).__name__, self.id))


class AggregateRoot(Entity):
    """Consistency boundary that records domain events for publication."""

    def __init__(self) -> None:
        self._events: list[DomainEvent] = []

    def record(self, event: DomainEvent) -> None:
        self._events.append(event)

    def pull_events(self) -> list[DomainEvent]:
        events, self._events = self._events, []
        return events
