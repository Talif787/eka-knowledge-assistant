"""Unit tests for the answer-quality metrics (pure, offline)."""

from __future__ import annotations

from eka.modules.evaluation.domain.metrics import (
    answer_relevance,
    context_precision,
    context_recall,
    faithfulness,
)


def test_context_recall_full_and_partial() -> None:
    contexts = ["databases can be queried efficiently"]
    assert context_recall(["databases", "queried"], contexts) == 1.0
    assert context_recall(["databases", "elephants"], contexts) == 0.5


def test_context_precision_counts_relevant_contexts() -> None:
    contexts = ["databases and queries", "unrelated museum opening hours"]
    assert context_precision("databases", contexts) == 0.5


def test_faithfulness_separates_grounded_from_hallucinated() -> None:
    contexts = ["databases organize information"]
    assert faithfulness("databases organize information", contexts) == 1.0
    assert faithfulness("elephants roam the savanna", contexts) == 0.0


def test_answer_relevance() -> None:
    assert answer_relevance("databases are queried", ["databases", "queried"]) == 1.0
    assert answer_relevance("nothing on topic here", ["databases"]) == 0.0


def test_empty_edge_cases_are_vacuous() -> None:
    assert context_recall([], ["anything"]) == 1.0
    assert context_precision("q", []) == 0.0
    assert faithfulness("", ["anything"]) == 1.0
