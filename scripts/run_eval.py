"""Run the answer-quality evaluation and gate on aggregate thresholds.

Hermetic: indexes the eval corpus in memory with the deterministic embedder and
runs the real fusion, reranking, guardrail, and grounded generation. No database
or network. Exits non-zero if any aggregate metric falls below its threshold, so
it can serve as a CI gate.
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

from eka.modules.evaluation.application.gate import Threshold, evaluate_gate
from eka.modules.evaluation.application.harness import EvaluationHarness
from eka.modules.evaluation.infrastructure.dataset_loader import load_dataset
from eka.modules.evaluation.infrastructure.in_memory_searcher import InMemorySearcher
from eka.modules.generation.domain.guardrails import PromptInjectionGuard
from eka.modules.generation.infrastructure.local_llm import LocalTemplateLanguageModel
from eka.modules.ingestion.infrastructure.embedding import HashingEmbeddingModel
from eka.modules.retrieval.infrastructure.reranker import LexicalReranker

_DATASET = Path(__file__).resolve().parents[1] / (
    "src/eka/modules/evaluation/datasets/smoke.json"
)
_TOP_K = 3
_THRESHOLDS = [
    Threshold("context_recall", 0.75),
    Threshold("context_precision", 0.30),
    Threshold("faithfulness", 0.75),
    Threshold("answer_relevance", 0.55),
]


async def _main() -> int:
    dataset = load_dataset(_DATASET)
    embedder = HashingEmbeddingModel(dimension=384)
    searcher = InMemorySearcher(embedder, LexicalReranker(), list(dataset.corpus))
    harness = EvaluationHarness(
        searcher=searcher,
        language_model=LocalTemplateLanguageModel(),
        guard=PromptInjectionGuard(),
    )
    report = await harness.run(dataset, tenant_id=uuid.uuid4(), top_k=_TOP_K)

    print("Per-case scores:")
    for result in report.results:
        print(
            f"  {result.case_id}: recall={result.context_recall:.2f} "
            f"precision={result.context_precision:.2f} "
            f"faithfulness={result.faithfulness:.2f} "
            f"relevance={result.answer_relevance:.2f}"
        )
    print("\nAggregates:")
    aggregates = report.aggregates()
    for name, value in aggregates.items():
        print(f"  {name}: {value:.3f}")

    passed, failures = evaluate_gate(report, _THRESHOLDS)
    print()
    if passed:
        print("EVAL GATE: PASS")
        return 0
    print("EVAL GATE: FAIL")
    for failure in failures:
        print(f"  - {failure}")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
