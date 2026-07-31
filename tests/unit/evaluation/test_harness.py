"""Unit test for the evaluation harness end to end (offline)."""

from __future__ import annotations

import asyncio
import uuid

from eka.modules.evaluation.application.harness import EvaluationHarness
from eka.modules.evaluation.domain.dataset import CorpusDoc, EvalCase, EvalDataset
from eka.modules.evaluation.infrastructure.in_memory_searcher import InMemorySearcher
from eka.modules.generation.domain.guardrails import PromptInjectionGuard
from eka.modules.generation.infrastructure.local_llm import LocalTemplateLanguageModel
from eka.modules.ingestion.infrastructure.embedding import HashingEmbeddingModel
from eka.modules.retrieval.infrastructure.reranker import LexicalReranker


def test_harness_scores_grounded_pipeline_highly() -> None:
    corpus = [
        CorpusDoc("db", "databases organize information so it can be queried efficiently"),
        CorpusDoc("weather", "a cold front brings rain along the coast"),
    ]
    cases = (EvalCase("c1", "how do databases query information", ("databases", "queried")),)
    dataset = EvalDataset(corpus=tuple(corpus), cases=cases)
    searcher = InMemorySearcher(
        HashingEmbeddingModel(dimension=384), LexicalReranker(), corpus
    )
    harness = EvaluationHarness(
        searcher=searcher,
        language_model=LocalTemplateLanguageModel(),
        guard=PromptInjectionGuard(),
    )

    report = asyncio.run(harness.run(dataset, uuid.uuid4(), top_k=2))
    aggregates = report.aggregates()
    # grounded pipeline sits well above hallucination levels (which score near 0)
    assert aggregates["faithfulness"] >= 0.6
    assert aggregates["context_recall"] >= 0.5
