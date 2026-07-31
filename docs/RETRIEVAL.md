# Retrieval

The retrieval context turns an indexed corpus into ranked, citable answers to a
query. It runs two search arms, fuses them, reranks the fused candidates, and
caches the result under an ACL-aware key.

## Flow

1. Build an ACL-aware cache key from tenant, collection filter, normalized query,
   and top_k. On a hit, return the cached results and stop.
2. Embed the query with the same model used at ingestion, so query and index
   vectors live in one space.
3. Retrieve candidates with the hybrid retriever (below).
4. Rerank the fused candidates and keep the top_k.
5. Cache the result and return it.

A cache failure degrades to a live search rather than an error: the cache is an
optimization, never a dependency of correctness.

## Hybrid retrieval

Two arms run against the `chunks` table, both scoped to the tenant (and to the
collection when a filter is supplied), so results never cross a boundary:

- Dense: cosine nearest neighbors over the pgvector `embedding` column, served by
  an HNSW index.
- Sparse: Postgres full-text search over a generated `tsvector` column
  (`text_tsv`), served by a GIN index.

The two ranked lists are combined with Reciprocal Rank Fusion (RRF), which needs
no score normalization across arms. That is why it is a robust default for fusing
dense and sparse signals whose score scales are not comparable.

## Reranking

The `Reranker` port reorders the fused candidates. The default `LexicalReranker`
is a deterministic, dependency-free implementation for development: it combines
the normalized retrieval score with query-term coverage and an exact-phrase
bonus. In production a cross-encoder model implements the same port; nothing else
in the flow changes.

## Caching

`SearchCache` is a port with two implementations: an in-memory cache (tests and
fallback) and a Redis cache (production). The key includes the tenant and the
collection filter, so a cached entry is never served across a tenant or
collection boundary. TTL is configurable (`EKA_SEARCH_CACHE_TTL_SECONDS`).

## Storage and migration

Migration `0003` enables the `vector` extension, converts `chunks.embedding` to
`vector(384)` with an HNSW index, and adds the generated `text_tsv` column with a
GIN index. The embedding representation changes, so existing chunks are truncated
and must be re-ingested (document content is retained in `document_contents`).

Because the storage engine changes, moving an existing dev database to this phase
means recreating the Postgres container on the `pgvector/pgvector:pg16` image:

```
docker compose down -v && docker compose up -d db redis
alembic upgrade head
# then re-run ingestion so chunks are rebuilt with vector embeddings
```

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| EKA_REDIS_URL | redis://localhost:6379/0 | Redis connection for the search cache |
| EKA_SEARCH_CACHE_TTL_SECONDS | 300 | Cache entry lifetime |
| EKA_SEARCH_POOL_SIZE | 50 | Candidates pulled per arm before fusion/rerank |
| EKA_SEARCH_DEFAULT_TOP_K | 5 | Default result count when a request omits top_k |
