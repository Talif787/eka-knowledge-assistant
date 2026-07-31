"""Hybrid retriever: dense vector search fused with sparse keyword search.

Dense search uses the pgvector HNSW index (cosine); sparse search uses the
generated tsvector column and Postgres full-text ranking. The two ranked lists
are fused with Reciprocal Rank Fusion. Both arms are tenant-scoped (and
collection-scoped when a filter is given) so results never cross a boundary.
"""
from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from eka.modules.ingestion.domain.embedding import Embedding
from eka.modules.retrieval.domain.fusion import reciprocal_rank_fusion
from eka.modules.retrieval.domain.search import ScoredChunk, SearchQuery

_VECTOR_SQL = text(
    """
    SELECT id, document_id, text
    FROM chunks
    WHERE tenant_id = :tenant
      AND (CAST(:collection AS uuid) IS NULL OR collection_id = CAST(:collection AS uuid))
    ORDER BY embedding <=> CAST(:qvec AS vector)
    LIMIT :pool
    """
)

_KEYWORD_SQL = text(
    """
    SELECT id, document_id, text
    FROM chunks
    WHERE tenant_id = :tenant
      AND (CAST(:collection AS uuid) IS NULL OR collection_id = CAST(:collection AS uuid))
      AND text_tsv @@ plainto_tsquery('english', :q)
    ORDER BY ts_rank(text_tsv, plainto_tsquery('english', :q)) DESC
    LIMIT :pool
    """
)


def _to_vector_literal(embedding: Embedding) -> str:
    return "[" + ",".join(repr(v) for v in embedding.values) + "]"


class PgVectorHybridRetriever:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def retrieve(
        self,
        tenant_id: uuid.UUID,
        query: SearchQuery,
        query_embedding: Embedding,
        pool_size: int,
    ) -> list[ScoredChunk]:
        collection = str(query.collection_id) if query.collection_id else None
        base_params = {
            "tenant": str(tenant_id),
            "collection": collection,
            "pool": pool_size,
        }

        vector_rows = (
            await self._session.execute(
                _VECTOR_SQL,
                {**base_params, "qvec": _to_vector_literal(query_embedding)},
            )
        ).all()
        keyword_rows = (
            await self._session.execute(
                _KEYWORD_SQL, {**base_params, "q": query.text}
            )
        ).all()

        catalog: dict[uuid.UUID, tuple[uuid.UUID, str]] = {}
        for row in [*vector_rows, *keyword_rows]:
            catalog[row.id] = (row.document_id, row.text)

        fused = reciprocal_rank_fusion(
            [[r.id for r in vector_rows], [r.id for r in keyword_rows]]
        )
        ordered = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)
        return [
            ScoredChunk(
                chunk_id=chunk_id,
                document_id=catalog[chunk_id][0],
                text=catalog[chunk_id][1],
                score=score,
            )
            for chunk_id, score in ordered[:pool_size]
        ]
