import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.observability.logging import get_request_id

logger = logging.getLogger(__name__)


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": get_request_id(),
            }
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "validation_error",
            "Request validation failed.",
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        code = {
            401: "unauthorized",
            403: "forbidden",
            404: "not_found",
            429: "rate_limited",
        }.get(exc.status_code, "http_error")
        return _error_response(exc.status_code, code, str(exc.detail))

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        return _error_response(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "rate_limited",
            "Rate limit exceeded.",
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception", exc_info=exc)
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "internal_error",
            "An unexpected error occurred.",
        )
