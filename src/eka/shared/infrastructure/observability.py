"""OpenTelemetry tracing setup.

Instrumentation is configuration-driven: when no OTLP endpoint is configured
the tracer stays a no-op, so local development carries no exporter overhead.
"""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def configure_tracing(*, service_name: str, otlp_endpoint: str | None) -> None:
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    if otlp_endpoint:
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint))
        )
    trace.set_tracer_provider(provider)


def configure_metrics(*, service_name: str, otlp_endpoint: str | None) -> None:
    """Set up the meter provider. Without an endpoint, metrics stay unexported."""
    from opentelemetry import metrics
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
        OTLPMetricExporter,
    )
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

    resource = Resource.create({"service.name": service_name})
    readers: list[PeriodicExportingMetricReader] = []
    if otlp_endpoint:
        readers.append(
            PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=otlp_endpoint))
        )
    provider = MeterProvider(resource=resource, metric_readers=readers)
    metrics.set_meter_provider(provider)
