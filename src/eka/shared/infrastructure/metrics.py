"""Application metrics.

Thin wrappers over OpenTelemetry instruments for the two operations worth
measuring: search and answer generation. Instruments are created lazily on first
use, after the meter provider is configured at startup. When no provider is
configured they bind to the API's no-op meter, so recording is a cheap no-op in
local development. This module imports only the metrics API, not the SDK.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from opentelemetry import metrics
from opentelemetry.metrics import Counter, Histogram


@dataclass(frozen=True)
class _Instruments:
    search_ops: Counter
    search_latency: Histogram
    answer_ops: Counter
    answer_latency: Histogram


@lru_cache(maxsize=1)
def _instruments() -> _Instruments:
    meter = metrics.get_meter("eka")
    return _Instruments(
        search_ops=meter.create_counter(
            "eka_search_operations", description="Search operations run"
        ),
        search_latency=meter.create_histogram(
            "eka_search_latency_ms", unit="ms", description="Search latency"
        ),
        answer_ops=meter.create_counter(
            "eka_answer_operations", description="Answers generated"
        ),
        answer_latency=meter.create_histogram(
            "eka_answer_latency_ms", unit="ms", description="Answer latency"
        ),
    )


def record_search(*, duration_ms: float, cache_hit: bool) -> None:
    instruments = _instruments()
    attributes: dict[str, str | int | bool] = {"cache_hit": cache_hit}
    instruments.search_ops.add(1, attributes)
    instruments.search_latency.record(duration_ms, attributes)


def record_answer(*, duration_ms: float, flagged: bool) -> None:
    instruments = _instruments()
    attributes: dict[str, str | int | bool] = {"flagged": flagged}
    instruments.answer_ops.add(1, attributes)
    instruments.answer_latency.record(duration_ms, attributes)
