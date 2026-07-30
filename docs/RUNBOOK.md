# Operational Runbook

## Readiness probe failing (/health/ready returns 503)
- Cause: the API cannot reach Postgres.
- Check: database reachable, credentials valid, `EKA_DATABASE_DSN` correct.
- Resolve: restore connectivity or fix the DSN; liveness stays green so the pod
  is not killed while the dependency recovers.

## Migrations out of sync
- Symptom: startup or queries fail on missing columns/tables.
- Check: `alembic current` versus `alembic heads`.
- Resolve: run `alembic upgrade head`. Migrations are backward compatible so a
  rollback to the previous image remains safe.

## Traces not appearing
- Cause: `EKA_OTLP_ENDPOINT` unset or collector unreachable.
- Check: endpoint value and collector health.
- Resolve: set the endpoint; tracing is a no-op by design when unset.

## High latency
- Inspect per-request `duration_ms` in the access logs and OpenTelemetry spans.
- Check database pool saturation (`EKA_DATABASE_POOL_SIZE`) and slow queries.

## Rollback
- Redeploy the previous immutable image tag. Because migrations follow
  expand-then-contract, the prior version runs against the current schema.
