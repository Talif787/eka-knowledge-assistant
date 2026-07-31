"""Unit tests for the local language model stand-in (offline)."""

from __future__ import annotations

import asyncio
import uuid

from eka.modules.generation.domain.answer import GroundedPrompt, PromptPassage
from eka.modules.generation.infrastructure.local_llm import LocalTemplateLanguageModel


def _collect(prompt: GroundedPrompt) -> str:
    async def run() -> str:
        return "".join([t async for t in LocalTemplateLanguageModel().stream(prompt)])

    return asyncio.run(run())


def test_streams_grounded_answer_with_citation() -> None:
    d = uuid.uuid4()
    passage = PromptPassage(1, uuid.uuid4(), d, "Databases organize information well.")
    prompt = GroundedPrompt("sys", "how do databases organize", (passage,))
    answer = _collect(prompt)
    assert "[1]" in answer
    assert "Databases organize" in answer


def test_no_passages_returns_cannot_answer() -> None:
    assert "could not find" in _collect(GroundedPrompt("sys", "q", ()))
