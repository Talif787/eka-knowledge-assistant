# Ingestion Pipeline (Phase 2)

## Flow

```
register document (Phase 1)         -> status REGISTERED
POST /v1/documents/{id}/content     -> verify hash, store text, enqueue job
worker dequeues (SKIP LOCKED)       -> status INGESTING
  extract -> chunk -> embed -> replace chunks (idempotent)
                                    -> status INDEXED
on repeated failure                 -> retry with backoff, then DEAD_LETTER + FAILED
```

## Components

- **Chunker** (`RecursiveCharacterChunker`): splits on paragraph, line, sentence,
  then word boundaries and packs to a target size with overlap. Strategy pattern
  behind the `Chunker` port.
- **Embedding model** (`HashingEmbeddingModel`): a deterministic, dependency-free
  local embedder for development and tests. A hosted semantic model implements the
  same `EmbeddingModel` port in production.
- **Job queue** (`SqlAlchemyJobQueue`): a database-backed queue using
  `SELECT ... FOR UPDATE SKIP LOCKED`. Enqueue is idempotent per
  `(document_id, version)`. Failures retry with exponential backoff; exhausted
  jobs move to a dead-letter state.
- **Worker** (`eka.worker`): polls the queue, runs the pipeline, and handles
  completion, retry, and dead-lettering with graceful shutdown.

## Why a database queue

At MVP scale a Postgres queue is transactional with domain writes, needs no extra
infrastructure, and handles meaningful throughput via row-level locking. The
`JobQueue` port lets it be replaced by SQS or Kafka at scale without changing the
pipeline.

## Running the worker

```bash
make worker            # local:  python -m eka.worker
# or in Docker:  the compose "worker" service starts automatically
```

## Inspecting results

```bash
GET /v1/documents/{id}/chunks        # chunks produced for a document
GET /v1/ingestion/jobs?status=dead_letter   # dead-letter queue visibility
```

## Idempotency and re-ingestion

Re-running a job replaces the document's chunks rather than appending, so retries
and re-ingestion never duplicate data. Content upload verifies the text against
the `content_hash` registered in Phase 1 before storing it.

## Note on embeddings storage

Embeddings are stored as JSONB in this phase to keep the stack runnable on stock
Postgres. Phase 3 migrates this to a pgvector column with an HNSW index when the
retrieval path introduces approximate-nearest-neighbor search.
