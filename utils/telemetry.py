"""OpenTelemetry tracing setup."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator

from config import get_settings
from utils.logging_config import logger

_tracer = None
_meter = None


def setup_telemetry() -> None:
    global _tracer, _meter
    settings = get_settings()
    if not settings.otel_enabled:
        return
    try:
        from opentelemetry import metrics, trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({"service.name": settings.otel_service_name})
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer(settings.otel_service_name)

        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

        reader = PeriodicExportingMetricReader(exporter)  # type: ignore[arg-type]
        meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
        metrics.set_meter_provider(meter_provider)
        _meter = metrics.get_meter(settings.otel_service_name)
        logger.info("OpenTelemetry initialized for %s", settings.otel_service_name)
    except Exception as exc:
        logger.warning("OpenTelemetry setup failed, continuing without tracing: %s", exc)


def get_tracer() -> Any:
    if _tracer is None:
        from opentelemetry import trace

        return trace.get_tracer("mainframe_copilot")
    return _tracer


@contextmanager
def trace_span(name: str, attributes: dict[str, Any] | None = None) -> Generator[None, None, None]:
    tracer = get_tracer()
    with tracer.start_as_current_span(name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, str(value))
        yield
