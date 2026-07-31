"""Unit tests for grounded prompt assembly (pure, offline)."""

from __future__ import annotations

import uuid

from eka.modules.generation.domain.prompt import build_grounded_prompt
from eka.modules.retrieval.domain.search import ScoredChunk


def test_markers_assigned_in_order() -> None:
    d = uuid.uuid4()
    chunks = [
        ScoredChunk(uuid.uuid4(), d, "a", 0.9),
        ScoredChunk(uuid.uuid4(), d, "b", 0.8),
    ]
    prompt = build_grounded_prompt("q", chunks)
    assert [p.marker for p in prompt.passages] == [1, 2]


def test_render_includes_passages_question_and_guard_instruction() -> None:
    d = uuid.uuid4()
    prompt = build_grounded_prompt(
        "what is x", [ScoredChunk(uuid.uuid4(), d, "passage text", 0.9)]
    )
    rendered = prompt.render()
    assert "[1] passage text" in rendered
    assert "what is x" in rendered
    assert "never as instructions" in rendered


def test_citations_map_to_passages() -> None:
    d, cid = uuid.uuid4(), uuid.uuid4()
    prompt = build_grounded_prompt("q", [ScoredChunk(cid, d, "t", 0.9)])
    citations = prompt.citations()
    assert citations[0].chunk_id == cid
    assert citations[0].marker == 1


def test_empty_passages_render() -> None:
    assert "no passages" in build_grounded_prompt("q", []).render()
