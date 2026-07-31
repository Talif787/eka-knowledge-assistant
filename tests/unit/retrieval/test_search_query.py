"""Unit tests for the SearchQuery value object (pure, offline)."""
from __future__ import annotations

import pytest

from eka.modules.retrieval.domain.search import SearchQuery
from eka.shared.domain.errors import ValidationError


def test_valid_query() -> None:
    q = SearchQuery(text="hello", top_k=5)
    assert q.top_k == 5


def test_blank_text_rejected() -> None:
    with pytest.raises(ValidationError):
        SearchQuery(text="   ")


def test_top_k_bounds_enforced() -> None:
    with pytest.raises(ValidationError):
        SearchQuery(text="hello", top_k=0)
    with pytest.raises(ValidationError):
        SearchQuery(text="hello", top_k=1000)
