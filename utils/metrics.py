"""Prometheus metrics for the Mainframe AI Copilot API."""

from __future__ import annotations

import time
from typing import Callable

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

INVESTIGATIONS_TOTAL = Counter(
    "copilot_investigations_total",
    "Total incident investigations",
    ["status"],
)

INVESTIGATION_DURATION = Histogram(
    "copilot_investigation_duration_seconds",
    "Investigation duration in seconds",
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
)

HTTP_REQUESTS_TOTAL = Counter(
    "copilot_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

HTTP_REQUEST_DURATION = Histogram(
    "copilot_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def record_investigation(duration_seconds: float, success: bool) -> None:
    status = "success" if success else "error"
    INVESTIGATIONS_TOTAL.labels(status=status).inc()
    INVESTIGATION_DURATION.observe(duration_seconds)


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path == "/metrics":
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        endpoint = request.url.path
        HTTP_REQUESTS_TOTAL.labels(
            method=request.method,
            endpoint=endpoint,
            status=str(response.status_code),
        ).inc()
        HTTP_REQUEST_DURATION.labels(method=request.method, endpoint=endpoint).observe(duration)
        return response
