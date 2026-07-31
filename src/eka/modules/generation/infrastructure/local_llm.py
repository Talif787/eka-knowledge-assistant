"""Local, deterministic language model stand-in.

For development and tests. It composes an answer strictly from the grounded
passages (selecting the sentence in each that best matches the question) and
cites them with [n] markers, then streams the result word by word. A real
provider (OpenAI, Anthropic, Bedrock) implements the same LanguageModel port;
nothing else in the pipeline changes.
"""
from __future__ import annotations

import re
from collections.abc import AsyncIterator

from eka.modules.generation.domain.answer import GroundedPrompt, PromptPassage

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_SENTENCE_RE = re.compile(r"[^.!?]+[.!?]?")
_MAX_PASSAGES_IN_ANSWER = 3


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


def _best_sentence(text: str, query_tokens: set[str]) -> str:
    sentences = [s.strip() for s in _SENTENCE_RE.findall(text) if s.strip()]
    if not sentences:
        return text.strip()
    best: str = max(sentences, key=lambda s: len(_tokens(s) & query_tokens))
    return best


def _compose(prompt: GroundedPrompt) -> str:
    if not prompt.passages:
        return (
            "I could not find relevant information in the retrieved context "
            "to answer that."
        )
    query_tokens = _tokens(prompt.question)
    selected: list[PromptPassage] = list(prompt.passages[:_MAX_PASSAGES_IN_ANSWER])
    parts = [
        f"{_best_sentence(p.text, query_tokens)} [{p.marker}]" for p in selected
    ]
    return "Based on the retrieved context: " + " ".join(parts)


class LocalTemplateLanguageModel:
    async def stream(self, prompt: GroundedPrompt) -> AsyncIterator[str]:
        answer = _compose(prompt)
        words = answer.split(" ")
        for index, word in enumerate(words):
            yield word if index == len(words) - 1 else word + " "
