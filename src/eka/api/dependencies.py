"""FastAPI dependency providers (composition root).

Wiring is explicit and constructor-based. A full DI framework is deliberately
avoided: FastAPI's Depends gives request-scoped injection with less magic,
which suits a modular monolith of this size.
"""
from __future__ import annotations

import uuid

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from eka.modules.documents.application.commands import (
    DeleteDocumentHandler,
    RegisterDocumentHandler,
)
from eka.modules.documents.application.queries import (
    GetDocumentHandler,
    ListDocumentsHandler,
)
from eka.modules.documents.infrastructure.repository import SqlAlchemyDocumentRepository
from eka.modules.documents.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


def get_engine(request: Request) -> AsyncEngine:
    return request.app.state.engine


def get_session_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    return request.app.state.session_factory


def get_unit_of_work(
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
) -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork(session_factory)


async def get_read_session(
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
) -> AsyncSession:
    async with session_factory() as session:
        yield session


def get_tenant_id(x_tenant_id: uuid.UUID = Header(alias="X-Tenant-ID")) -> uuid.UUID:
    """Resolve the tenant from a header.

    A placeholder for Phase 5, where the tenant is derived from the verified JWT
    rather than trusted from a client header.
    """
    return x_tenant_id


def register_document_handler(
    uow: SqlAlchemyUnitOfWork = Depends(get_unit_of_work),
) -> RegisterDocumentHandler:
    return RegisterDocumentHandler(uow)


def delete_document_handler(
    uow: SqlAlchemyUnitOfWork = Depends(get_unit_of_work),
) -> DeleteDocumentHandler:
    return DeleteDocumentHandler(uow)


def get_document_handler(
    session: AsyncSession = Depends(get_read_session),
) -> GetDocumentHandler:
    return GetDocumentHandler(SqlAlchemyDocumentRepository(session))


def list_documents_handler(
    session: AsyncSession = Depends(get_read_session),
) -> ListDocumentsHandler:
    return ListDocumentsHandler(SqlAlchemyDocumentRepository(session))
