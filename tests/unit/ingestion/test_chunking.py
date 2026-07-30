"""Unit tests for the recursive character chunker (pure, offline)."""
from __future__ import annotations

import pytest

from eka.modules.ingestion.domain.chunking import ChunkingConfig, RecursiveCharacterChunker
from eka.shared.domain.errors import ValidationError


def test_empty_text_yields_no_pieces() -> None:
    assert RecursiveCharacterChunker().split("   ") == []


def test_short_text_is_single_piece() -> None:
    pieces = RecursiveCharacterChunker().split("a short document")
    assert len(pieces) == 1
    assert pieces[0].ordinal == 0
    assert pieces[0].text == "a short document"


def test_long_text_splits_into_multiple_pieces_within_size() -> None:
    config = ChunkingConfig(chunk_size=100, chunk_overlap=20)
    text = " ".join(f"word{i}" for i in range(300))
    pieces = RecursiveCharacterChunker(config).split(text)
    assert len(pieces) > 1
    assert all(len(p.text) <= config.chunk_size + config.chunk_overlap for p in pieces)
    assert [p.ordinal for p in pieces] == list(range(len(pieces)))


def test_overlap_carries_context_between_chunks() -> None:
    config = ChunkingConfig(chunk_size=60, chunk_overlap=20)
    text = " ".join(f"token{i:03d}" for i in range(60))
    pieces = RecursiveCharacterChunker(config).split(text)
    # consecutive chunks should share some trailing/leading vocabulary
    first_words = set(pieces[0].text.split())
    second_words = set(pieces[1].text.split())
    assert first_words & second_words


def test_prefers_paragraph_boundaries() -> None:
    config = ChunkingConfig(chunk_size=50, chunk_overlap=0)
    text = "First paragraph here.\n\nSecond paragraph here.\n\nThird one."
    pieces = RecursiveCharacterChunker(config).split(text)
    assert len(pieces) >= 2


def test_invalid_config_rejected() -> None:
    with pytest.raises(ValidationError):
        ChunkingConfig(chunk_size=0)
    with pytest.raises(ValidationError):
        ChunkingConfig(chunk_size=100, chunk_overlap=100)
