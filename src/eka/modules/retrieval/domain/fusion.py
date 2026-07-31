"""Reciprocal Rank Fusion.

Combines several ranked lists into one score per item using sum(1 / (k + rank)).
RRF needs no score normalization across arms, which is why it is a robust default
for fusing dense and sparse retrieval that produce incomparable score scales.
"""
from __future__ import annotations

import uuid

DEFAULT_RRF_K = 60


def reciprocal_rank_fusion(
    rankings: list[list[uuid.UUID]], k: int = DEFAULT_RRF_K
) -> dict[uuid.UUID, float]:
    if k < 1:
        raise ValueError("rrf k must be >= 1")
    scores: dict[uuid.UUID, float] = {}
    for ranking in rankings:
        for rank, item_id in enumerate(ranking, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
    return scores
