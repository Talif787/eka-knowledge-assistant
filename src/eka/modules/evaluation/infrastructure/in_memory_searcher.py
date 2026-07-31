"""In-memory Searcher for hermetic evaluation.

Indexes the eval corpus in memory and runs the same algorithm as the production
retriever (dense cosine plus keyword overlap, fused with RRF, then reranked),
without a database. This keeps the eval gate fast, deterministic, and free of
infrastructure, while still exercising the real fusion and reranking logic.
"""

from __future__ import annotations

import re
import uuid

from eka.modules.evaluation.domain.dataset import CorpusDoc
from eka.modules.ingestion.domain.embedding import Embedding, EmbeddingModel
from eka.modules.retrieval.domain.fusion import reciprocal_rank_fusion
from eka.modules.retrieval.domain.search import Reranker, ScoredChunk, SearchQuery

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_NAMESPACE = uuid.UUID("00000000-0000-0000-0000-000000000006")


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


def _doc_uuid(doc_id: str) -> uuid.UUID:
    return uuid.uuid5(_NAMESPACE, doc_id)


class InMemorySearcher:
    def __init__(
        self,
        embedder: EmbeddingModel,
        reranker: Reranker,
        corpus: list[CorpusDoc],
    ) -> None:
        self._embedder = embedder
        self._reranker = reranker
        self._corpus = corpus
        self._doc_embeddings: list[Embedding] | None = None

    async def _ensure_embedded(self) -> list[Embedding]:
        if self._doc_embeddings is None:
            self._doc_embeddings = await self._embedder.embed(
                [doc.text for doc in self._corpus]
            )
        return self._doc_embeddings

    async def handle(self, tenant_id: uuid.UUID, query: SearchQuery) -> list[ScoredChunk]:
        doc_embeddings = await self._ensure_embedded()
        query_embedding = (await self._embedder.embed([query.text]))[0]

        sims = sorted(
            range(len(self._corpus)),
            key=lambda i: query_embedding.cosine_similarity(doc_embeddings[i]),
            reverse=True,
        )
        vector_ids = [_doc_uuid(self._corpus[i].id) for i in sims]

        query_tokens = _tokens(query.text)
        overlaps = [
            (i, len(_tokens(self._corpus[i].text) & query_tokens))
            for i in range(len(self._corpus))
        ]
        keyword_ids = [
            _doc_uuid(self._corpus[i].id)
            for i, overlap in sorted(overlaps, key=lambda x: x[1], reverse=True)
            if overlap > 0
        ]

        fused = reciprocal_rank_fusion([vector_ids, keyword_ids])
        by_id = {_doc_uuid(doc.id): doc for doc in self._corpus}
        ordered = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)
        candidates = [
            ScoredChunk(
                chunk_id=chunk_id,
                document_id=chunk_id,
                text=by_id[chunk_id].text,
                score=score,
            )
            for chunk_id, score in ordered
        ]
        return await self._reranker.rerank(query.text, candidates, query.top_k)
