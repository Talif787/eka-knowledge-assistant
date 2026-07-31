"""Unit tests for the Chunk entity and its text value object (pure, offline)."""

from __future__ import annotations

import uuid

import pytest

from eka.modules.ingestion.domain.chunk import Chunk, ChunkText
from eka.modules.ingestion.domain.embedding import Embedding
from eka.shared.domain.errors import ValidationError


def _embedding() -> Embedding:
    return Embedding((0.6, 0.8))


def test_chunk_text_rejects_blank() -> None:
    with pytest.raises(ValidationError):
        ChunkText("   ")


def test_chunk_create_populates_fields() -> None:
    chunk = Chunk.create(
        tenant_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        collection_id=uuid.uuid4(),
        document_version=1,
        ordinal=0,
        text="a chunk of text",
        embedding=_embedding(),
    )
    assert chunk.ordinal == 0
    assert chunk.text.value == "a chunk of text"
    assert chunk.embedding.dimension == 2


def test_negative_ordinal_rejected() -> None:
    with pytest.raises(ValidationError):
        Chunk.create(
            tenant_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            collection_id=uuid.uuid4(),
            document_version=1,
            ordinal=-1,
            text="text",
            embedding=_embedding(),
        )
