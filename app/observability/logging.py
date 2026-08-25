import logging
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar

from pythonjsonlogger.json import JsonFormatter
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"

_request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    return _request_id_ctx.get()


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "-"
        return True


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        token = _request_id_ctx.set(request_id)
        try:
            response = await call_next(request)
        finally:
            _request_id_ctx.reset(token)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response


def configure_logging(log_level: str) -> None:
    handler = logging.StreamHandler()
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(
        JsonFormatter(
            "{levelname}{asctime}{name}{message}{request_id}",
            style="{",
            rename_fields={"levelname": "level", "asctime": "timestamp"},
        )
    )

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(log_level.upper())

    for noisy in ("uvicorn.access",):
        logging.getLogger(noisy).setLevel(logging.WARNING)
