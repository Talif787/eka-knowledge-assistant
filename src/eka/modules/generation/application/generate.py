"""Answer generation use case.

Pipeline: retrieve tenant-scoped passages, sanitize them against prompt
injection, assemble a grounded prompt with citation markers, then stream the
answer. Emits a sources event first (so a client can render citations before
tokens arrive), then token events, then a done event.
"""
from __future__ import annotations

import dataclasses
import uuid
from collections.abc import AsyncIterator

from eka.modules.generation.domain.answer import (
    EventType,
    GroundedPrompt,
    LanguageModel,
    Searcher,
)
from eka.modules.generation.domain.guardrails import PromptInjectionGuard
from eka.modules.generation.domain.prompt import (
    DEFAULT_SYSTEM_PROMPT,
    build_grounded_prompt,
)
from eka.modules.retrieval.domain.search import ScoredChunk, SearchQuery
from eka.shared.infrastructure.logging import get_logger

logger = get_logger(__name__)


class GenerateAnswerHandler:
    def __init__(
        self,
        *,
        searcher: Searcher,
        guard: PromptInjectionGuard,
        language_model: LanguageModel,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    ) -> None:
        self._searcher = searcher
        self._guard = guard
        self._language_model = language_model
        self._system_prompt = system_prompt

    def _sanitize(self, chunks: list[ScoredChunk]) -> tuple[list[ScoredChunk], bool]:
        cleaned: list[ScoredChunk] = []
        flagged = False
        for chunk in chunks:
            text, hit = self._guard.scan(chunk.text)
            flagged = flagged or hit
            cleaned.append(dataclasses.replace(chunk, text=text))
        return cleaned, flagged

    async def stream(
        self, tenant_id: uuid.UUID, query: SearchQuery
    ) -> AsyncIterator[dict[str, object]]:
        chunks = await self._searcher.handle(tenant_id, query)
        sanitized, flagged = self._sanitize(chunks)
        prompt: GroundedPrompt = build_grounded_prompt(
            query.text, sanitized, self._system_prompt
        )
        if flagged:
            logger.warning("prompt_injection_flagged", tenant_id=str(tenant_id))

        yield {
            "type": EventType.SOURCES,
            "flagged": flagged,
            "citations": [
                {
                    "marker": c.marker,
                    "chunk_id": str(c.chunk_id),
                    "document_id": str(c.document_id),
                }
                for c in prompt.citations()
            ],
        }
        async for token in self._language_model.stream(prompt):
            yield {"type": EventType.TOKEN, "text": token}
        yield {"type": EventType.DONE}
        logger.info(
            "answer_completed", tenant_id=str(tenant_id), passages=len(sanitized)
        )
