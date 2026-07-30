"""Documents REST API (v1).

REST is chosen over GraphQL for this resource-oriented CRUD surface: the access
patterns are simple, HTTP caching and idempotency semantics apply cleanly, and
tooling (OpenAPI) is first-class.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Response, status

from eka.api.dependencies import (
    delete_document_handler,
    get_document_handler,
    get_tenant_id,
    list_documents_handler,
    register_document_handler,
)
from eka.modules.documents.application.commands import (
    DeleteDocumentCommand,
    DeleteDocumentHandler,
    RegisterDocumentCommand,
    RegisterDocumentHandler,
)
from eka.modules.documents.application.queries import (
    GetDocumentHandler,
    GetDocumentQuery,
    ListDocumentsHandler,
    ListDocumentsQuery,
)
from eka.modules.documents.presentation.schemas import (
    DocumentListResponse,
    DocumentResponse,
    PageMeta,
    RegisterDocumentRequest,
)
from eka.shared.domain.pagination import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    PageRequest,
    Sort,
    SortDirection,
)

router = APIRouter(prefix="/v1/documents", tags=["documents"])


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def register_document(
    body: RegisterDocumentRequest,
    response: Response,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    handler: RegisterDocumentHandler = Depends(register_document_handler),
) -> DocumentResponse:
    dto = await handler.handle(
        RegisterDocumentCommand(
            tenant_id=tenant_id,
            collection_id=body.collection_id,
            title=body.title,
            source_type=body.source_type,
            source_uri=body.source_uri,
            content_hash=body.content_hash,
        )
    )
    response.headers["Location"] = f"/v1/documents/{dto.id}"
    return DocumentResponse.from_dto(dto)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    handler: GetDocumentHandler = Depends(get_document_handler),
) -> DocumentResponse:
    dto = await handler.handle(GetDocumentQuery(tenant_id=tenant_id, document_id=document_id))
    return DocumentResponse.from_dto(dto)


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    handler: ListDocumentsHandler = Depends(list_documents_handler),
    collection_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="created_at"),
    sort_dir: SortDirection = Query(default=SortDirection.DESC),
) -> DocumentListResponse:
    page = await handler.handle(
        ListDocumentsQuery(
            tenant_id=tenant_id,
            page=PageRequest(limit=limit, offset=offset, sort=Sort(sort_by, sort_dir)),
            collection_id=collection_id,
        )
    )
    return DocumentListResponse(
        items=[DocumentResponse.from_dto(d) for d in page.items],
        meta=PageMeta(
            total=page.total, limit=page.limit, offset=page.offset, has_more=page.has_more
        ),
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    handler: DeleteDocumentHandler = Depends(delete_document_handler),
) -> Response:
    await handler.handle(
        DeleteDocumentCommand(tenant_id=tenant_id, document_id=document_id)
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
