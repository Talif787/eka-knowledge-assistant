"""ASGI application factory.

The factory pattern keeps construction testable: tests build an app with
overridden settings and dependencies without importing a module-level singleton.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from redis.asyncio import Redis

from eka.api.errors import register_exception_handlers
from eka.api.health import router as health_router
from eka.api.middleware import (
    AccessLogMiddleware,
    CorrelationIdMiddleware,
    SecurityHeadersMiddleware,
)
from eka.config import Settings, get_settings
from eka.modules.documents.presentation.router import router as documents_router
from eka.modules.ingestion.infrastructure.embedding import HashingEmbeddingModel
from eka.modules.ingestion.presentation.router import router as ingestion_router
from eka.modules.retrieval.infrastructure.reranker import LexicalReranker
from eka.modules.retrieval.presentation.router import router as retrieval_router
from eka.shared.infrastructure.database import create_engine, create_session_factory
from eka.shared.infrastructure.logging import configure_logging, get_logger
from eka.shared.infrastructure.observability import configure_tracing

logger = get_logger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    configure_logging(level=settings.log_level, json_logs=settings.json_logs)
    configure_tracing(
        service_name=settings.service_name, otlp_endpoint=settings.otlp_endpoint
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_engine(
            settings.database_dsn,
            echo=settings.database_echo,
            pool_size=settings.database_pool_size,
        )
        app.state.engine = engine
        app.state.session_factory = create_session_factory(engine)
        app.state.redis = Redis.from_url(settings.redis_url)
        app.state.embedding_model = HashingEmbeddingModel(settings.embedding_dimension)
        app.state.reranker = LexicalReranker()
        app.state.redis = Redis.from_url(settings.redis_url)
        app.state.embedding_model = HashingEmbeddingModel(settings.embedding_dimension)
        app.state.reranker = LexicalReranker()
        SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
        logger.info("application_started", environment=settings.environment)
        try:
            yield
        finally:
            await app.state.redis.aclose()
            await engine.dispose()
            logger.info("application_stopped")

    app = FastAPI(
        title="Enterprise Knowledge Assistant API",
        version="1.0.0",
        root_path=settings.api_root_path,
        lifespan=lifespan,
    )

    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(CorrelationIdMiddleware)

    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(documents_router)
    app.include_router(ingestion_router)
    app.include_router(retrieval_router)

    FastAPIInstrumentor.instrument_app(app)
    return app
