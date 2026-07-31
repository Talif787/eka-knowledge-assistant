"""Search API (v1)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from eka.api.dependencies import get_tenant_id, search_handler
from eka.modules.retrieval.application.dto import SearchResultDTO
from eka.modules.retrieval.application.search import SearchHandler
from eka.modules.retrieval.domain.search import SearchQuery
from eka.modules.retrieval.presentation.schemas import (
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)

router = APIRouter(tags=["retrieval"])


@router.post("/v1/search", response_model=SearchResponse)
async def search(
    body: SearchRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    handler: SearchHandler = Depends(search_handler),
) -> SearchResponse:
    query = SearchQuery(
        text=body.query, top_k=body.top_k, collection_id=body.collection_id
    )
    results = await handler.handle(tenant_id, query)
    dtos = [SearchResultDTO.from_scored_chunk(r) for r in results]
    return SearchResponse(
        query=body.query, results=[SearchResultItem.from_dto(d) for d in dtos]
    )
