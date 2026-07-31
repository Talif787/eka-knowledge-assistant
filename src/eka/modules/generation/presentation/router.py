"""Answer API (v1): grounded, cited answers streamed as Server-Sent Events."""
from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from eka.api.dependencies import generate_answer_handler, get_tenant_id
from eka.modules.generation.application.generate import GenerateAnswerHandler
from eka.modules.generation.presentation.schemas import AnswerRequest
from eka.modules.retrieval.domain.search import SearchQuery

router = APIRouter(tags=["generation"])


@router.post("/v1/answer")
async def answer(
    body: AnswerRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    handler: GenerateAnswerHandler = Depends(generate_answer_handler),
) -> StreamingResponse:
    query = SearchQuery(
        text=body.query, top_k=body.top_k, collection_id=body.collection_id
    )

    async def event_stream() -> AsyncIterator[bytes]:
        async for event in handler.stream(tenant_id, query):
            yield f"data: {json.dumps(event)}\n\n".encode()

    return StreamingResponse(event_stream(), media_type="text/event-stream")
