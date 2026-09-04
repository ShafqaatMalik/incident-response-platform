from collections.abc import Generator
from unittest.mock import Mock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings


@pytest.fixture
def _tracing_enabled(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    monkeypatch.setenv("OTEL_TRACES_ENABLED", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


async def test_app_starts_with_tracing_fully_enabled(_tracing_enabled: None) -> None:
    """Builds a fresh app (not the module-level singleton, which is already
    imported with tracing disabled) with OTEL_TRACES_ENABLED=true, so FastAPI
    instrumentation, SQLAlchemy instrumentation, and Cloud Trace exporter
    construction all actually run — the exporter is patched out so no real
    GCP/ADC call is made.
    """
    with patch("app.observability.tracing.CloudTraceSpanExporter", return_value=Mock()):
        from app.main import create_app

        app = create_app()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
