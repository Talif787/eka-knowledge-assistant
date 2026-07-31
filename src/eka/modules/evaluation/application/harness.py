"""Evaluation harness.

Runs each dataset case through the same pieces the real answer path uses
(retrieve, sanitize, ground, generate) and scores the result with the metric
proxies. Returns a report of per-case and aggregate scores.
"""

from __future__ import annotations

import dataclasses
import uuid

from eka.modules.evaluation.domain.dataset import (
    CaseResult,
    EvalDataset,
    EvalReport,
)
from eka.modules.evaluation.domain.metrics import (
    answer_relevance,
    context_precision,
    context_recall,
    faithfulness,
)
from eka.modules.generation.domain.answer import LanguageModel, Searcher
from eka.modules.generation.domain.guardrails import PromptInjectionGuard
from eka.modules.generation.domain.prompt import (
    DEFAULT_SYSTEM_PROMPT,
    build_grounded_prompt,
)
from eka.modules.retrieval.domain.search import SearchQuery


class EvaluationHarness:
    def __init__(
        self,
        *,
        searcher: Searcher,
        language_model: LanguageModel,
        guard: PromptInjectionGuard,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    ) -> None:
        self._searcher = searcher
        self._language_model = language_model
        self._guard = guard
        self._system_prompt = system_prompt

    async def run(self, dataset: EvalDataset, tenant_id: uuid.UUID, top_k: int) -> EvalReport:
        results: list[CaseResult] = []
        for case in dataset.cases:
            query = SearchQuery(text=case.question, top_k=top_k)
            chunks = await self._searcher.handle(tenant_id, query)
            sanitized = [
                dataclasses.replace(c, text=self._guard.scan(c.text)[0]) for c in chunks
            ]
            contexts = [c.text for c in sanitized]
            prompt = build_grounded_prompt(case.question, sanitized, self._system_prompt)
            answer = "".join([token async for token in self._language_model.stream(prompt)])
            expected = list(case.expected_keywords)
            results.append(
                CaseResult(
                    case_id=case.id,
                    context_recall=context_recall(expected, contexts),
                    context_precision=context_precision(case.question, contexts),
                    faithfulness=faithfulness(answer, contexts),
                    answer_relevance=answer_relevance(answer, expected),
                )
            )
        return EvalReport(results=tuple(results))
