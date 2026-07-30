# Architecture

## Style and boundaries

EKA is a modular monolith. Each bounded context lives under `src/eka/modules/<context>`
and is split into four layers with strictly inward dependencies:

- **domain**: aggregates, value objects, domain events, repository ports. Pure
  Python, no framework imports.
- **application**: use cases as command and query handlers (CQRS-lite), DTOs,
  and the unit-of-work contract. Depends only on domain abstractions.
- **infrastructure**: SQLAlchemy models, repository adapters, unit of work. Implements
  the domain ports.
- **presentation**: FastAPI routers and Pydantic schemas. Maps transport to use cases.

Cross-cutting concerns live in `src/eka/shared` (domain kernel, logging, tracing,
database) and `src/eka/api` (app factory, middleware, error envelope, health, DI).

## Dependency flow

```
presentation -> application -> domain <- infrastructure
```

The domain sits at the center. Infrastructure depends on the domain (it implements
its ports); nothing depends on infrastructure except the composition root
(`api/dependencies.py` and `api/app.py`), which wires concrete adapters to ports.

## Why CQRS-lite

Command and query handlers are separated so the read and write paths can evolve
and scale independently. Reads use a plain read session; writes go through the
unit of work to guarantee transactional consistency and event integrity. Full
event sourcing is intentionally not used: audit needs are met by dedicated audit
logs (Phase 5) without the added complexity.

## Idempotency and consistency

Document registration is idempotent by content hash within a tenant, enforced
both in the handler (lookup before insert) and by a unique constraint. This makes
retried ingestion safe, which matters once the async ingestion pipeline (Phase 2)
can deliver a message more than once.

## Observability

Every request receives a correlation id (generated or propagated via `X-Request-ID`),
bound into the logging context and returned in the response. FastAPI and SQLAlchemy
are instrumented with OpenTelemetry; the exporter is a no-op unless an OTLP endpoint
is configured, so local runs carry no overhead.

## Extraction path

Because modules communicate only through their public application services and
own their data, a context (for example, ingestion) can be lifted into a standalone
service by replacing in-process calls with transport calls and pointing the module
at its own database. This mirrors the phased evolution in the production
architecture document.
