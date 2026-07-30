"""Unit-of-Work contract.

Application handlers depend on this abstraction, never on the ORM session
directly, keeping the application layer persistence-agnostic.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from eka.modules.documents.domain.repository import DocumentRepository


@runtime_checkable
class UnitOfWork(Protocol):
    documents: DocumentRepository

    async def __aenter__(self) -> "UnitOfWork": ...
    async def __aexit__(self, *exc: object) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
