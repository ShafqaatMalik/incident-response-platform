from contextlib import AbstractContextManager

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Span

from app.core.config import Settings

tracer = trace.get_tracer("app.agents")


def configure_tracing(app: FastAPI, settings: Settings) -> None:
    if not settings.otel_traces_enabled:
        return

    provider = TracerProvider(
        resource=Resource.create({SERVICE_NAME: "incident-response-platform"})
    )
    provider.add_span_processor(BatchSpanProcessor(CloudTraceSpanExporter()))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument()


def anthropic_call_span(agent_name: str, model: str) -> AbstractContextManager[Span]:
    return tracer.start_as_current_span(
        f"{agent_name}.anthropic_call",
        attributes={"gen_ai.system": "anthropic", "gen_ai.request.model": model},
    )
