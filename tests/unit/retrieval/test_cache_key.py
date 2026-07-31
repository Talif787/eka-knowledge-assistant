"""Unit tests for the ACL-aware cache key (pure, offline)."""
from __future__ import annotations

import uuid

from eka.modules.retrieval.application.cache_key import build_cache_key


def test_normalizes_whitespace_and_case() -> None:
    t, c = uuid.uuid4(), uuid.uuid4()
    assert build_cache_key(t, c, "Hello   World", 5) == build_cache_key(t, c, "hello world", 5)


def test_isolated_by_tenant() -> None:
    c = uuid.uuid4()
    assert build_cache_key(uuid.uuid4(), c, "q", 5) != build_cache_key(uuid.uuid4(), c, "q", 5)


def test_isolated_by_collection() -> None:
    t = uuid.uuid4()
    assert build_cache_key(t, uuid.uuid4(), "q", 5) != build_cache_key(t, uuid.uuid4(), "q", 5)


def test_isolated_by_top_k() -> None:
    t, c = uuid.uuid4(), uuid.uuid4()
    assert build_cache_key(t, c, "q", 5) != build_cache_key(t, c, "q", 10)


def test_key_is_prefixed_by_tenant() -> None:
    t = uuid.uuid4()
    assert build_cache_key(t, None, "q", 5).startswith(f"search:{t}:")
