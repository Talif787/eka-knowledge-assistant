# EKA: Enterprise Knowledge Assistant

A production-grade, retrieval-augmented knowledge assistant that answers
employees' questions from private company documents with grounded, cited
answers. Ask a question and the answer streams back with inline citation markers
that trace to the exact source passages, so a claim is never separated from where
it came from.

**Live demo: [<LIVE_URL>](https://eka-frontend-five.vercel.app/)**  (open, no signup; each visitor gets an isolated tenant
sandbox). Frontend repo:
[eka-frontend](https://github.com/Talif787/eka-frontend).

A short demo clip is coming soon. In the meantime, try it live at the link above: sign in (a workspace is created for you), register a document, then ask a question in the Answer view and watch the response stream in with citations.

The system registers documents, chunks and embeds them through a background
worker, runs hybrid retrieval, and streams a grounded answer, all multi-tenant
and scoped by a verified JWT. It is built as a modular monolith with hexagonal,
domain-driven boundaries, so each bounded context can later be extracted into its
own service without a rewrite.

## Why a modular monolith

At MVP scale a single deployable is faster to build, cheaper to operate, and
easier to keep consistent than a service fleet. The code is organized by bounded
context with hexagonal boundaries (domain, application, infrastructure,
presentation) and inward-only dependencies, so each module can later be extracted
into its own service without a rewrite. Complexity is added only when a measured
scaling threshold demands it.

## Technology stack and rationale

- **Python 3.12 + FastAPI**: async-first, first-class OpenAPI, strong typing.
- **Pydantic v2 / pydantic-settings**: validation at the edge and config from the
  environment (Twelve-Factor).
- **SQLAlchemy 2.0 (async) + asyncpg + Alembic**: typed ORM, non-blocking I/O,
  versioned migrations.
- **Postgres + pgvector, Redis**: vector and keyword retrieval, plus a queue and
  cache.
- **structlog**: JSON structured logs bound to a correlation id.
- **OpenTelemetry**: vendor-neutral tracing, configuration-driven exporters.
- **pytest / ruff / mypy (strict)**: tests, linting/formatting, static types.

## Architecture at a glance

```
Request -> Middleware (correlation id, security headers, access log)
        -> Router (presentation, Pydantic schemas)
        -> Command/Query handler (application, CQRS split)
        -> Aggregate (domain invariants + events)
        -> Repository port -> SQLAlchemy adapter (infrastructure)
        -> Postgres
```

Dependencies point inward. The domain layer imports nothing from the framework,
which is why its unit tests run without any infrastructure. See
`docs/ARCHITECTURE.md` for the full breakdown and the module map.

Bounded contexts: documents, ingestion, retrieval, generation, identity, and
evaluation. Answers and citations are pluggable behind ports: the repo ships a
dependency-free, deterministic local embedder and generator for zero-cost
operation, and a hosted model implements the same port for production with no
application changes.

## Local development

Prerequisites: Python 3.12 and Docker.

```bash
cp .env.example .env
make install                 # install app + dev dependencies
make up                      # start Postgres, Redis, the API, and the worker
# or run the API against a local Postgres:
make migrate && make run
```

The interactive API docs are served at `http://localhost:8000/docs` and the
OpenAPI 3.1 document at `http://localhost:8000/openapi.json`.

## Testing

```bash
make test-unit               # pure-domain tests, no database required
# integration + API tests need a database:
EKA_TEST_DATABASE_DSN=postgresql+asyncpg://eka:eka@localhost:5432/eka_test make test
```

Unit tests cover domain invariants and the document state machine. Integration
tests exercise the repository, retrieval, and the ingestion pipeline against a
disposable Postgres with pgvector; they are skipped automatically when
`EKA_TEST_DATABASE_DSN` is unset. The suite is 100 tests, unit and integration.

The answer-quality gate runs offline and needs no database:

```bash
python scripts/run_eval.py     # scores retrieval and grounding, gates on thresholds
```

It runs in CI after the tests. See `docs/EVALUATION.md`.

## Configuration

All settings are read from the environment with the `EKA_` prefix and validated
at startup. See `.env.example` and `docs/CONFIGURATION.md`.

## API surface

| Method | Path                    | Purpose                          |
|--------|-------------------------|----------------------------------|
| POST   | /v1/auth/token          | Dev-only: mint a bearer token (stands in for an IdP) |
| POST   | /v1/documents           | Register a document (idempotent) |
| GET    | /v1/documents           | List documents (paged, sorted)   |
| GET    | /v1/documents/{id}      | Fetch a document                 |
| DELETE | /v1/documents/{id}      | Soft-delete a document           |
| GET    | /health/live            | Liveness probe                   |
| GET    | /health/ready           | Readiness probe (checks DB)      |
| POST   | /v1/documents/{id}/content | Upload text, verify hash, enqueue ingestion |
| GET    | /v1/documents/{id}/chunks  | List chunks produced for a document |
| GET    | /v1/ingestion/jobs         | List ingestion jobs (status, DLQ)   |
| POST   | /v1/search                 | Hybrid search: vector + keyword, reranked, cached |
| POST   | /v1/answer                 | Grounded, cited answer streamed as SSE |

All `/v1` endpoints except `/v1/auth/token` require a bearer token
(`Authorization: Bearer <jwt>`); the tenant is taken from the verified token, not
from a client header. In development, mint one at `/v1/auth/token`.

Registration is idempotent by `(tenant_id, content_hash)`: a repeated request for
identical content returns the existing document instead of duplicating it.

## Deployment

The live demo runs a right-sized, low-cost stack:

```
Browser
  -> Vercel        Next.js 15 frontend (eka-frontend)
  -> Fly.io        FastAPI API + background worker (this repo)
       -> Neon     Postgres + pgvector
       -> Upstash  Redis
```

The service is containerized (multi-stage, non-root) with a health check, and
`alembic upgrade head` runs as a release step so migrations apply before a new
version goes live (they are expand-then-contract, so rollbacks are safe). The API
and the worker run as two process groups from the same image; `fly.toml` is the
deployment as code.

A Kubernetes path is also included: a Helm chart and a Terraform configuration,
with a local `kind` path that runs entirely free (in-cluster Postgres and Redis).
See `docs/DEPLOYMENT.md` and `docs/SCALING.md`.

## Troubleshooting and runbook

See `docs/RUNBOOK.md` for common failure modes (readiness failing, migration
drift, tracing not exporting) and their resolutions. For logs, traces, and
metrics, see `docs/OBSERVABILITY.md`.

## Status

Feature-complete against the API and deployed. All planned work is done:

1. Documents context foundation.
2. Ingestion pipeline: chunking, embedding port, async worker, DLQ, idempotency.
3. Retrieval: hybrid search (pgvector + full text), re-ranking, Redis caching.
4. Generation: prompt assembly, LLM port, SSE streaming, citations, guardrails.
5. Identity: tenant-scoped JWT auth.
6. Evaluation harness and CI quality gate.
7. Deployment: Docker, Fly.io (API + worker), managed Postgres and Redis, plus a
   Helm and Terraform Kubernetes path with a free local `kind` option.

Next steps, deliberately out of scope for this cut: a real identity provider
(OIDC) with RBAC and ABAC, and retrieval-time ACL enforcement.

## Note on authentication

The public demo runs an open token endpoint so anyone can try it in an isolated
tenant sandbox. It is demo-mode auth, not a real identity system. A production
deployment would disable the dev token and add proper user authentication (OIDC)
with role and attribute-based access, and enforce access control at retrieval
time.
