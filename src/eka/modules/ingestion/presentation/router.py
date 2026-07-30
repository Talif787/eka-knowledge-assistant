"""Ingestion REST API (v1): upload content, inspect chunks and jobs."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status

from eka.api.dependencies import (
    get_tenant_id,
    ingestion_chunk_repository,
    ingestion_list_jobs,
    upload_content_handler,
)
from eka.modules.ingestion.application.content import UploadDocumentContentHandler
from eka.modules.ingestion.application.dto import ChunkDTO
from eka.modules.ingestion.application.job_queries import ListJobsHandler, ListJobsQuery
from eka.modules.ingestion.infrastructure.repository import SqlAlchemyChunkRepository
from eka.modules.ingestion.presentation.schemas import (
    ChunkListResponse,
    ChunkResponse,
    ContentAcceptedResponse,
    JobListResponse,
    JobResponse,
    UploadContentRequest,
)
from eka.shared.domain.pagination import DEFAULT_LIMIT, MAX_LIMIT, PageRequest

router = APIRouter(tags=["ingestion"])


@router.post(
    "/v1/documents/{document_id}/content",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ContentAcceptedResponse,
)
async def upload_content(
    document_id: uuid.UUID,
    body: UploadContentRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    handler: UploadDocumentContentHandler = Depends(upload_content_handler),
) -> ContentAcceptedResponse:
    await handler.handle(tenant_id, document_id, body.content)
    return ContentAcceptedResponse(document_id=document_id)


@router.get(
    "/v1/documents/{document_id}/chunks", response_model=ChunkListResponse
)
async def list_chunks(
    document_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    repository: SqlAlchemyChunkRepository = Depends(ingestion_chunk_repository),
) -> ChunkListResponse:
    chunks = await repository.list_for_document(tenant_id, document_id)
    dtos = [ChunkDTO.from_entity(c) for c in chunks]
    return ChunkListResponse(
        items=[ChunkResponse.from_dto(d) for d in dtos], count=len(dtos)
    )


@router.get("/v1/ingestion/jobs", response_model=JobListResponse)
async def list_jobs(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    handler: ListJobsHandler = Depends(ingestion_list_jobs),
    job_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
) -> JobListResponse:
    page = await handler.handle(
        ListJobsQuery(
            tenant_id=tenant_id,
            page=PageRequest(limit=limit, offset=offset),
            status=job_status,
        )
    )
    return JobListResponse(items=[JobResponse.from_dto(d) for d in page.items])
