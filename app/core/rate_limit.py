from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.core.config import get_settings


def rate_limit_key(request: Request) -> str:
    api_key = request.headers.get("X-API-Key")
    return api_key if api_key else get_remote_address(request)


limiter = Limiter(key_func=rate_limit_key, headers_enabled=True)


def rate_limit_value() -> str:
    return f"{get_settings().rate_limit_per_minute}/minute"
