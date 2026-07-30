"""SQLAlchemy Unit of Work for the ingestion context."""
from __future__ import annotations

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from eka.modules.ingestion.application.ports import ChunkRepository, ContentStore
from eka.modules.ingestion.infrastructure.repository import (
    SqlAlchemyChunkRepository,
    SqlAlchemyContentStore,
)


class SqlAlchemyIngestionUnitOfWork:
    chunks: ChunkRepository
    content: ContentStore

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> SqlAlchemyIngestionUnitOfWork:
        self._session = self._session_factory()
        self.chunks = SqlAlchemyChunkRepository(self._session)
        self.content = SqlAlchemyContentStore(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        assert self._session is not None
        try:
            if exc_type is not None:
                await self._session.rollback()
        finally:
            await self._session.close()
            self._session = None

    async def commit(self) -> None:
        assert self._session is not None
        await self._session.commit()

    async def rollback(self) -> None:
        assert self._session is not None
        await self._session.rollback()
