"""Quality gate: fail when an aggregate metric falls below its threshold."""

from __future__ import annotations

from dataclasses import dataclass

from eka.modules.evaluation.domain.dataset import EvalReport


@dataclass(frozen=True, slots=True)
class Threshold:
    metric: str
    minimum: float


def evaluate_gate(report: EvalReport, thresholds: list[Threshold]) -> tuple[bool, list[str]]:
    aggregates = report.aggregates()
    failures: list[str] = []
    for threshold in thresholds:
        value = aggregates.get(threshold.metric)
        if value is None:
            failures.append(f"unknown metric: {threshold.metric}")
        elif value < threshold.minimum:
            failures.append(
                f"{threshold.metric} {value:.3f} below minimum {threshold.minimum:.3f}"
            )
    return (not failures, failures)
