# Observability

The service emits three signals: structured logs, distributed traces, and
metrics. All three are configuration-driven, so local development carries no
exporter overhead and production turns them on by setting an OTLP endpoint.

## Logs

Logging is structured (structlog) and JSON-rendered. The two use cases worth
watching log an outcome line with latency and result counts: `search_completed`
and `search_cache_hit` carry `results` and `duration_ms`; `answer_completed`
carries `passages`, `flagged`, and `duration_ms`. A flagged prompt injection
attempt logs `prompt_injection_flagged` at warning level.

## Traces

Tracing uses OpenTelemetry. FastAPI and SQLAlchemy are instrumented, so each
request and each database query is a span, with the request span as parent. When
`EKA_OTLP_ENDPOINT` is unset the tracer is a no-op, so there is no overhead
locally. Set the endpoint to export spans to any OTLP-compatible backend (for
example a collector, Jaeger, or Tempo).

## Metrics

Metrics also use OpenTelemetry. Two operations are instrumented:

- **search**: a counter (`eka_search_operations`) and a latency histogram
  (`eka_search_latency_ms`), both tagged with `cache_hit`.
- **answer**: a counter (`eka_answer_operations`) and a latency histogram
  (`eka_answer_latency_ms`), both tagged with `flagged`.

Instruments are created lazily on first use, after the meter provider is
configured at startup. When no OTLP endpoint is configured they bind to the
API's no-op meter, so recording is a cheap no-op locally. With an endpoint set,
a periodic reader exports them over OTLP.

Attributes are deliberately low-cardinality (booleans, not identifiers) so the
metric time series stay cheap to store and query. High-cardinality detail (tenant
ids, document ids) lives in traces and logs, not in metric labels.

## Configuration

A single setting drives export for both traces and metrics:

```
EKA_OTLP_ENDPOINT=http://localhost:4317
```

Leave it unset in local development. See `docs/CONFIGURATION.md` for the full
settings reference.
