# Enterprise Knowledge Assistant (EKA)

A production-grade, retrieval-augmented knowledge assistant that answers
employees' questions from private company documents with grounded citations.
This repository is a modular monolith built for clean extraction into services
as scale demands (see the evolution path in the architecture documents).

This codebase is delivered in phases. **Phase 1 (this cut)** establishes the
foundation and the first vertical slice (the Documents context) end to end:
domain, application, infrastructure, presentation, persistence, observability,
tests, containers, and CI.

## Why a modular monolith

At MVP scale a single deployable is faster to build, cheaper to operate, and
easier to keep consistent than a service fleet. The code is organized by
bounded context with hexagonal boundaries (domain, application, infrastructure,
presentation) and inward-only dependencies, so each module can later be
extracted into its own service without a rewrite. Complexity is added only when
a measured scaling threshold demands it.

## Technology stack and rationale

- **Python 3.12 + FastAPI**: async-first, first-class OpenAPI, strong typing.
- **Pydantic v2 / pydantic-settings**: validation at the edge and config from the
  environment (Twelve-Factor).
- **SQLAlchemy 2.0 (async) + asyncpg + Alembic**: typed ORM, non-blocking I/O,
  versioned migrations.
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

## Local development

Prerequisites: Python 3.12 and Docker.

```bash
cp .env.example .env
make install                 # install app + dev dependencies
make up                      # start Postgres, Redis, and the API via Docker
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
tests exercise the repository against a disposable Postgres. They are skipped
automatically when `EKA_TEST_DATABASE_DSN` is unset.

## Configuration

All settings are read from the environment with the `EKA_` prefix and validated
at startup. See `.env.example` and `docs/CONFIGURATION.md`.

## API surface (Phase 1)

| Method | Path                    | Purpose                          |
|--------|-------------------------|----------------------------------|
| POST   | /v1/documents           | Register a document (idempotent) |
| GET    | /v1/documents           | List documents (paged, sorted)   |
| GET    | /v1/documents/{id}      | Fetch a document                 |
| DELETE | /v1/documents/{id}      | Soft-delete a document           |
| GET    | /health/live            | Liveness probe                   |
| GET    | /health/ready           | Readiness probe (checks DB)      |
| POST   | /v1/documents/{id}/content | Upload text, verify hash, enqueue ingestion |
| GET    | /v1/documents/{id}/chunks  | List chunks produced for a document |
| GET    | /v1/ingestion/jobs         | List ingestion jobs (status, DLQ)   |

Registration is idempotent by `(tenant_id, content_hash)`: a repeated request
for identical content returns the existing document instead of duplicating it.

## Deployment

The service is containerized (multi-stage, non-root) and ships with a health
check. Kubernetes manifests, Helm chart, and Terraform arrive in Phase 7. Run the worker alongside the API to process ingestion jobs (`make worker` or the
compose `worker` service). Run
`alembic upgrade head` before starting the API; migrations are backward
compatible (expand-then-contract) so rollbacks are safe.

## Troubleshooting and runbook

See `docs/RUNBOOK.md` for common failure modes (readiness failing, migration
drift, tracing not exporting) and their resolutions.

## Roadmap

1. Documents context foundation (done).
2. Ingestion pipeline: chunking, embedding port, async worker, DLQ, idempotency (done).
3. Retrieval: hybrid search (pgvector + full text), re-ranking, Redis caching.
4. Generation: prompt assembly, LLM port, SSE streaming, citations, guardrails.
5. AuthN/AuthZ: OIDC/JWT, RBAC + ABAC, retrieval-time ACL enforcement.
6. Evaluation harness and CI quality gate.
7. Observability depth, Kubernetes/Helm, Terraform, full operational docs.
