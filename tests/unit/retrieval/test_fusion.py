"""Unit tests for Reciprocal Rank Fusion (pure, offline)."""
from __future__ import annotations

import uuid

import pytest

from eka.modules.retrieval.domain.fusion import reciprocal_rank_fusion


def test_item_ranked_high_in_both_arms_wins() -> None:
    a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    scores = reciprocal_rank_fusion([[a, b, c], [a, c, b]])
    ranked = sorted(scores, key=lambda i: scores[i], reverse=True)
    assert ranked[0] == a


def test_item_in_one_arm_still_scored() -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    scores = reciprocal_rank_fusion([[a], [b]])
    assert set(scores) == {a, b}
    assert scores[a] == scores[b]  # both rank 1 in their arm


def test_higher_k_flattens_contribution() -> None:
    a = uuid.uuid4()
    assert reciprocal_rank_fusion([[a]], k=10)[a] > reciprocal_rank_fusion([[a]], k=100)[a]


def test_invalid_k_rejected() -> None:
    with pytest.raises(ValueError):
        reciprocal_rank_fusion([[uuid.uuid4()]], k=0)
