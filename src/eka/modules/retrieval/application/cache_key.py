"""ACL-aware cache key construction.

The key includes the tenant and the collection filter, so a cached result can
never be served across a tenant or collection boundary. The query text is
normalized so trivially different spellings share a cache entry.
"""
from __future__ import annotations

import hashlib
import uuid


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def build_cache_key(
    tenant_id: uuid.UUID,
    collection_id: uuid.UUID | None,
    query_text: str,
    top_k: int,
) -> str:
    collection = str(collection_id) if collection_id is not None else "*"
    material = f"{tenant_id}|{collection}|{top_k}|{_normalize(query_text)}"
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return f"search:{tenant_id}:{digest}"
