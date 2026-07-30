"""Unit tests for pagination primitives."""
from __future__ import annotations

import pytest

from eka.shared.domain.errors import ValidationError
from eka.shared.domain.pagination import MAX_LIMIT, Page, PageRequest


def test_page_request_rejects_bad_limit() -> None:
    with pytest.raises(ValidationError):
        PageRequest(limit=0)
    with pytest.raises(ValidationError):
        PageRequest(limit=MAX_LIMIT + 1)


def test_page_request_rejects_negative_offset() -> None:
    with pytest.raises(ValidationError):
        PageRequest(offset=-1)


def test_has_more_true_when_more_remain() -> None:
    page = Page(items=[1, 2, 3], total=10, limit=3, offset=0)
    assert page.has_more is True


def test_has_more_false_on_last_page() -> None:
    page = Page(items=[1, 2], total=5, limit=3, offset=3)
    assert page.has_more is False
