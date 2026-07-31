"""Evaluation dataset and result value objects."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CorpusDoc:
    id: str
    text: str


@dataclass(frozen=True, slots=True)
class EvalCase:
    id: str
    question: str
    expected_keywords: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvalDataset:
    corpus: tuple[CorpusDoc, ...]
    cases: tuple[EvalCase, ...]


@dataclass(frozen=True, slots=True)
class CaseResult:
    case_id: str
    context_recall: float
    context_precision: float
    faithfulness: float
    answer_relevance: float


@dataclass(frozen=True, slots=True)
class EvalReport:
    results: tuple[CaseResult, ...]

    def _mean(self, attr: str) -> float:
        if not self.results:
            return 0.0
        total = sum(float(getattr(r, attr)) for r in self.results)
        return total / len(self.results)

    def aggregates(self) -> dict[str, float]:
        return {
            "context_recall": self._mean("context_recall"),
            "context_precision": self._mean("context_precision"),
            "faithfulness": self._mean("faithfulness"),
            "answer_relevance": self._mean("answer_relevance"),
        }
