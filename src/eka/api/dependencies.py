"""FastAPI dependency providers (composition root).

Wiring is explicit and constructor-based. A full DI framework is deliberately
avoided: FastAPI's Depends gives request-scoped injection with less magic,
which suits a modular monolith of this size.
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from typing import cast

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
    return cast(AsyncEngine, request.app.state.engine)


def get_session_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    return cast("async_sessionmaker[AsyncSession]", request.app.state.session_factory)


def get_unit_of_work(
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
) -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork(session_factory)


async def get_read_session(
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
) -> AsyncGenerator[AsyncSession, None]:
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


# --- Ingestion context wiring (Phase 2) ---
from eka.config import get_settings  # noqa: E402
from eka.modules.ingestion.application.content import (  # noqa: E402
    UploadDocumentContentHandler,
)
from eka.modules.ingestion.application.job_queries import ListJobsHandler  # noqa: E402
from eka.modules.ingestion.infrastructure.queue import SqlAlchemyJobQueue  # noqa: E402
from eka.modules.ingestion.infrastructure.repository import (  # noqa: E402
    SqlAlchemyChunkRepository,
)
from eka.modules.ingestion.infrastructure.unit_of_work import (  # noqa: E402
    SqlAlchemyIngestionUnitOfWork,
)


def get_job_queue(
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
) -> SqlAlchemyJobQueue:
    return SqlAlchemyJobQueue(session_factory)


def upload_content_handler(
    session: AsyncSession = Depends(get_read_session),
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
    queue: SqlAlchemyJobQueue = Depends(get_job_queue),
) -> UploadDocumentContentHandler:
    from eka.modules.documents.application.queries import GetDocumentHandler

    return UploadDocumentContentHandler(
        get_document=GetDocumentHandler(SqlAlchemyDocumentRepository(session)),
        uow_factory=lambda: SqlAlchemyIngestionUnitOfWork(session_factory),
        queue=queue,
        max_attempts=get_settings().ingestion_max_attempts,
    )


def ingestion_chunk_repository(
    session: AsyncSession = Depends(get_read_session),
) -> SqlAlchemyChunkRepository:
    return SqlAlchemyChunkRepository(session)


def ingestion_list_jobs(
    session: AsyncSession = Depends(get_read_session),
) -> ListJobsHandler:
    return ListJobsHandler(session)


# --- Retrieval context wiring (Phase 3) ---
from redis.asyncio import Redis  # noqa: E402

from eka.modules.ingestion.domain.embedding import EmbeddingModel  # noqa: E402
from eka.modules.retrieval.application.search import SearchHandler  # noqa: E402
from eka.modules.retrieval.domain.search import Reranker  # noqa: E402
from eka.modules.retrieval.infrastructure.pgvector_retriever import (  # noqa: E402
    PgVectorHybridRetriever,
)
from eka.modules.retrieval.infrastructure.redis_cache import RedisSearchCache  # noqa: E402


def get_embedding_model(request: Request) -> EmbeddingModel:
    return cast(EmbeddingModel, request.app.state.embedding_model)


def get_reranker(request: Request) -> Reranker:
    return cast(Reranker, request.app.state.reranker)


def get_redis(request: Request) -> Redis:
    return cast(Redis, request.app.state.redis)


def get_retriever(
    session: AsyncSession = Depends(get_read_session),
) -> PgVectorHybridRetriever:
    return PgVectorHybridRetriever(session)


def get_search_cache(redis: Redis = Depends(get_redis)) -> RedisSearchCache:
    return RedisSearchCache(redis)


def search_handler(
    embedder: EmbeddingModel = Depends(get_embedding_model),
    retriever: PgVectorHybridRetriever = Depends(get_retriever),
    reranker: Reranker = Depends(get_reranker),
    cache: RedisSearchCache = Depends(get_search_cache),
) -> SearchHandler:
    settings = get_settings()
    return SearchHandler(
        embedder=embedder,
        retriever=retriever,
        reranker=reranker,
        cache=cache,
        pool_size=settings.search_pool_size,
        cache_ttl_seconds=settings.search_cache_ttl_seconds,
    )

# --- Generation context wiring (Phase 4) ---
from eka.modules.generation.application.generate import (  # noqa: E402
    GenerateAnswerHandler,
)
from eka.modules.generation.domain.answer import LanguageModel  # noqa: E402
from eka.modules.generation.domain.guardrails import PromptInjectionGuard  # noqa: E402


def get_language_model(request: Request) -> LanguageModel:
    return cast(LanguageModel, request.app.state.language_model)


def generate_answer_handler(
    searcher: SearchHandler = Depends(search_handler),
    language_model: LanguageModel = Depends(get_language_model),
) -> GenerateAnswerHandler:
    return GenerateAnswerHandler(
        searcher=searcher,
        guard=PromptInjectionGuard(),
        language_model=language_model,
    )
