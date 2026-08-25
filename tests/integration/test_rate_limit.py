import pytest
from httpx import AsyncClient

from app.core.config import get_settings


async def test_rate_limit_returns_429_once_exceeded(
    client: AsyncClient, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "2")
    get_settings.cache_clear()
    try:
        statuses = [
            (await client.get("/documents", headers=auth_headers)).status_code for _ in range(3)
        ]
    finally:
        get_settings.cache_clear()

    assert statuses[:2] == [200, 200]
    assert statuses[2] == 429
