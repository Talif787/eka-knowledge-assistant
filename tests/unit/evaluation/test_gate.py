"""Unit tests for the eval quality gate (pure, offline)."""

from __future__ import annotations

from eka.modules.evaluation.application.gate import Threshold, evaluate_gate
from eka.modules.evaluation.domain.dataset import CaseResult, EvalReport


def _report(recall: float, precision: float, faith: float, relevance: float) -> EvalReport:
    return EvalReport(results=(CaseResult("c1", recall, precision, faith, relevance),))


def test_passes_when_all_above_thresholds() -> None:
    passed, failures = evaluate_gate(
        _report(1.0, 0.9, 0.9, 0.9), [Threshold("faithfulness", 0.8)]
    )
    assert passed
    assert not failures


def test_fails_when_below_threshold() -> None:
    passed, failures = evaluate_gate(
        _report(1.0, 0.9, 0.5, 0.9), [Threshold("faithfulness", 0.8)]
    )
    assert not passed
    assert len(failures) == 1


def test_unknown_metric_is_a_failure() -> None:
    passed, failures = evaluate_gate(
        _report(1.0, 1.0, 1.0, 1.0), [Threshold("nonexistent", 0.5)]
    )
    assert not passed
