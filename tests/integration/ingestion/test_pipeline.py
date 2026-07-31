"""End-to-end ingestion pipeline test.

Registers a document, stores matching content, runs the pipeline, and asserts the
document is INDEXED with chunks persisted. Requires a live Postgres.
"""
from __future__ import annotations

import hashlib
import uuid

import pytest

from eka.modules.documents.application.lifecycle import DocumentLifecycleService
from eka.modules.documents.domain.document import (
    ContentHash,
    Document,
    DocumentStatus,
    SourceType,
    Title,
)
from eka.modules.documents.infrastructure.repository import SqlAlchemyDocumentRepository
from eka.modules.documents.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from eka.modules.ingestion.application.jobs import IngestionJob
from eka.modules.ingestion.application.pipeline import IngestDocumentHandler
from eka.modules.ingestion.domain.chunking import ChunkingConfig, RecursiveCharacterChunker
from eka.modules.ingestion.infrastructure.embedding import HashingEmbeddingModel
from eka.modules.ingestion.infrastructure.repository import (
    SqlAlchemyChunkRepository,
    SqlAlchemyContentStore,
)
from eka.modules.ingestion.infrastructure.unit_of_work import (
    SqlAlchemyIngestionUnitOfWork,
)
from tests.conftest import requires_db

pytestmark = [pytest.mark.asyncio, requires_db]

CONTENT = (
    ("Paragraph one about databases. " * 20)
    + "\n\n"
    + ("Paragraph two about retrieval. " * 20)
)


async def test_pipeline_indexes_document_and_persists_chunks(session_factory) -> None:
    tenant = uuid.uuid4()
    collection = uuid.uuid4()
    content_hash = hashlib.sha256(CONTENT.encode()).hexdigest()

    doc = Document.register(
        tenant_id=tenant, collection_id=collection, title=Title("Guide"),
        source_type=SourceType.UPLOAD, source_uri="s3://b/k",
        content_hash=ContentHash(content_hash),
    )
    async with session_factory() as s:
        await SqlAlchemyDocumentRepository(s).add(doc)
        await SqlAlchemyContentStore(s).put(tenant, doc.id, CONTENT)
        await s.commit()

    handler = IngestDocumentHandler(
        uow_factory=lambda: SqlAlchemyIngestionUnitOfWork(session_factory),
        lifecycle=DocumentLifecycleService(SqlAlchemyUnitOfWork(session_factory)),
        chunker=RecursiveCharacterChunker(ChunkingConfig(chunk_size=200, chunk_overlap=40)),
        embedder=HashingEmbeddingModel(dimension=384),
    )
    job = IngestionJob(
        id=uuid.uuid4(), tenant_id=tenant, document_id=doc.id, collection_id=collection,
        document_version=1, attempts=0, max_attempts=5,
    )
    await handler.handle(job)

    async with session_factory() as s:
        chunks = await SqlAlchemyChunkRepository(s).list_for_document(tenant, doc.id)
        reloaded = await SqlAlchemyDocumentRepository(s).get(tenant, doc.id)
    assert len(chunks) > 1
    assert chunks[0].embedding.dimension == 384
    assert reloaded is not None and reloaded.status is DocumentStatus.INDEXED


async def test_pipeline_is_idempotent_on_rerun(session_factory) -> None:
    tenant, collection = uuid.uuid4(), uuid.uuid4()
    content_hash = hashlib.sha256(CONTENT.encode()).hexdigest()
    doc = Document.register(
        tenant_id=tenant, collection_id=collection, title=Title("Guide"),
        source_type=SourceType.UPLOAD, source_uri="s3://b/k",
        content_hash=ContentHash(content_hash),
    )
    async with session_factory() as s:
        await SqlAlchemyDocumentRepository(s).add(doc)
        await SqlAlchemyContentStore(s).put(tenant, doc.id, CONTENT)
        await s.commit()

    handler = IngestDocumentHandler(
        uow_factory=lambda: SqlAlchemyIngestionUnitOfWork(session_factory),
        lifecycle=DocumentLifecycleService(SqlAlchemyUnitOfWork(session_factory)),
        chunker=RecursiveCharacterChunker(ChunkingConfig(chunk_size=200, chunk_overlap=40)),
        embedder=HashingEmbeddingModel(dimension=384),
    )
    job = IngestionJob(
        id=uuid.uuid4(), tenant_id=tenant, document_id=doc.id, collection_id=collection,
        document_version=1, attempts=0, max_attempts=5,
    )
    await handler.handle(job)
    async with session_factory() as s:
        first = len(await SqlAlchemyChunkRepository(s).list_for_document(tenant, doc.id))
    # rerun: mark ingesting is allowed from indexed, chunks replaced not duplicated
    await handler.handle(job)
    async with session_factory() as s:
        second = len(await SqlAlchemyChunkRepository(s).list_for_document(tenant, doc.id))
    assert first == second
