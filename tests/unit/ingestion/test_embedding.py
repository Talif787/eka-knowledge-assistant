"""Unit tests for the embedding value object and local model (pure, offline)."""
from __future__ import annotations

import asyncio
import math

import pytest

from eka.modules.ingestion.domain.embedding import Embedding
from eka.modules.ingestion.infrastructure.embedding import HashingEmbeddingModel
from eka.shared.domain.errors import ValidationError


def test_embedding_rejects_empty() -> None:
    with pytest.raises(ValidationError):
        Embedding(())


def test_cosine_similarity_bounds() -> None:
    a = Embedding((1.0, 0.0))
    b = Embedding((1.0, 0.0))
    c = Embedding((0.0, 1.0))
    assert math.isclose(a.cosine_similarity(b), 1.0)
    assert math.isclose(a.cosine_similarity(c), 0.0)


def test_cosine_dimension_mismatch_raises() -> None:
    with pytest.raises(ValidationError):
        Embedding((1.0, 0.0)).cosine_similarity(Embedding((1.0,)))


def _embed(model: HashingEmbeddingModel, texts: list[str]) -> list[Embedding]:
    return asyncio.run(model.embed(texts))


def test_model_output_is_normalized_and_correct_dimension() -> None:
    model = HashingEmbeddingModel(dimension=128)
    (vec,) = _embed(model, ["query optimization in databases"])
    assert vec.dimension == 128
    norm = math.sqrt(sum(v * v for v in vec.values))
    assert math.isclose(norm, 1.0, abs_tol=1e-9)


def test_model_is_deterministic() -> None:
    model = HashingEmbeddingModel(dimension=64)
    a = _embed(model, ["repeatable text"])[0]
    b = _embed(model, ["repeatable text"])[0]
    assert a.values == b.values


def test_related_texts_more_similar_than_unrelated() -> None:
    model = HashingEmbeddingModel(dimension=256)
    a, b, c = _embed(
        model,
        [
            "database indexing and query optimization",
            "query optimization for database indexing",
            "sunny weather on the coast",
        ],
    )
    assert a.cosine_similarity(b) > a.cosine_similarity(c)
