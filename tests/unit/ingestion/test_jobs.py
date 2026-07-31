"""Unit tests for the retry/backoff policy (pure, offline)."""

from __future__ import annotations

from eka.modules.ingestion.application.jobs import JobStatus, compute_backoff_seconds


def test_backoff_is_zero_before_first_attempt() -> None:
    assert compute_backoff_seconds(0) == 0


def test_backoff_grows_exponentially() -> None:
    assert compute_backoff_seconds(1) == 5
    assert compute_backoff_seconds(2) == 10
    assert compute_backoff_seconds(3) == 20


def test_backoff_is_capped() -> None:
    assert compute_backoff_seconds(50) == 3600


def test_status_values_are_stable() -> None:
    assert JobStatus.DEAD_LETTER.value == "dead_letter"
    assert {s.value for s in JobStatus} == {
        "pending",
        "processing",
        "completed",
        "dead_letter",
    }
