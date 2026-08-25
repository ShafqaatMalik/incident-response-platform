import time
from collections.abc import Awaitable, Callable

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
)


def _route_path(request: Request) -> str:
    route = request.scope.get("route")
    return route.path if route is not None else request.url.path


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        path = _route_path(request)
        REQUEST_COUNT.labels(
            method=request.method, path=path, status_code=response.status_code
        ).inc()
        REQUEST_LATENCY.labels(method=request.method, path=path).observe(duration)
        return response


def render_metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
