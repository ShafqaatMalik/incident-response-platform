from unittest.mock import Mock, patch

from fastapi import FastAPI

from app.core.config import Settings
from app.observability.tracing import configure_tracing


def _settings(*, otel_traces_enabled: bool) -> Settings:
    return Settings(
        api_key="test-api-key",
        database_url="postgresql+asyncpg://postgres:postgres@localhost:5432/test",
        otel_traces_enabled=otel_traces_enabled,
    )


def test_disabled_by_default_does_nothing() -> None:
    app = FastAPI()
    with (
        patch("app.observability.tracing.CloudTraceSpanExporter") as exporter,
        patch("app.observability.tracing.FastAPIInstrumentor") as fastapi_instrumentor,
        patch("app.observability.tracing.SQLAlchemyInstrumentor") as sqlalchemy_instrumentor,
    ):
        configure_tracing(app, _settings(otel_traces_enabled=False))

    exporter.assert_not_called()
    fastapi_instrumentor.instrument_app.assert_not_called()
    sqlalchemy_instrumentor.assert_not_called()


def test_enabled_wires_exporter_and_both_instrumentors() -> None:
    app = FastAPI()
    with (
        patch("app.observability.tracing.CloudTraceSpanExporter", return_value=Mock()) as exporter,
        patch("app.observability.tracing.FastAPIInstrumentor") as fastapi_instrumentor,
        patch("app.observability.tracing.SQLAlchemyInstrumentor") as sqlalchemy_instrumentor,
    ):
        configure_tracing(app, _settings(otel_traces_enabled=True))

    exporter.assert_called_once()
    fastapi_instrumentor.instrument_app.assert_called_once_with(app)
    sqlalchemy_instrumentor.return_value.instrument.assert_called_once_with()
