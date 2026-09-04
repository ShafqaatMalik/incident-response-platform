from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.triage import TriageFailedError
from app.core.config import get_settings
from app.models.daily_spend import DailySpend
from app.models.incident import Incident, IncidentStatus
from app.models.schemas import TriageResult
from app.orchestration.triage_workflow import run_triage
from app.policies.pricing_policy import calculate_cost

TRIAGE_RESULT = TriageResult(
    severity="critical",
    affected_service="checkout-api",
    symptoms=["elevated 500s", "latency spike"],
    initial_evidence=["500s in logs", "p99 latency 4x baseline"],
)


async def test_happy_path_transitions_detected_to_triaged(db_session: AsyncSession) -> None:
    incident = Incident(
        trigger="Checkout API returning 500s",
        evidence=["500s in logs"],
        status=IncidentStatus.DETECTED.value,
    )
    db_session.add(incident)
    await db_session.commit()

    with patch(
        "app.orchestration.triage_workflow.call_triage_agent_with_retry",
        AsyncMock(return_value=TRIAGE_RESULT),
    ):
        result = await run_triage(incident, db_session, get_settings())

    assert result.status == IncidentStatus.TRIAGED.value
    assert result.severity == "critical"
    assert result.affected_service == "checkout-api"
    assert result.symptoms == ["elevated 500s", "latency spike"]
    # original evidence is preserved, agent's evidence is appended, deduped
    assert result.evidence == ["500s in logs", "p99 latency 4x baseline"]
    assert result.escalation_reason is None


async def test_failure_path_transitions_detected_to_escalated(db_session: AsyncSession) -> None:
    incident = Incident(
        trigger="Checkout API returning 500s",
        evidence=["500s in logs"],
        status=IncidentStatus.DETECTED.value,
    )
    db_session.add(incident)
    await db_session.commit()

    with patch(
        "app.orchestration.triage_workflow.call_triage_agent_with_retry",
        AsyncMock(side_effect=TriageFailedError("Triage failed after retry: boom")),
    ):
        result = await run_triage(incident, db_session, get_settings())

    assert result.status == IncidentStatus.ESCALATED.value
    assert result.severity is None
    assert result.escalation_reason is not None
    assert "boom" in result.escalation_reason


async def test_evidence_dedupe_preserves_order(db_session: AsyncSession) -> None:
    incident = Incident(
        trigger="Checkout API returning 500s",
        evidence=["500s in logs"],
        status=IncidentStatus.DETECTED.value,
    )
    db_session.add(incident)
    await db_session.commit()

    duplicate_result = TriageResult(
        severity="high",
        affected_service="checkout-api",
        symptoms=["elevated 500s"],
        initial_evidence=["500s in logs", "new evidence"],
    )

    with patch(
        "app.orchestration.triage_workflow.call_triage_agent_with_retry",
        AsyncMock(return_value=duplicate_result),
    ):
        result = await run_triage(incident, db_session, get_settings())

    assert result.evidence == ["500s in logs", "new evidence"]


def _fake_client(parsed_output: TriageResult | None, input_tokens: int, output_tokens: int) -> Mock:
    """A fake Anthropic client, for tests that need the real _request_triage/
    call_triage_agent_with_retry bodies to run (so spend recording actually
    fires) rather than mocking call_triage_agent_with_retry itself, which
    would skip straight past the recording code under test.
    """
    response = SimpleNamespace(
        parsed_output=parsed_output,
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens),
    )
    client = Mock()
    client.messages.parse = AsyncMock(return_value=response)
    return client


async def test_spend_is_recorded_after_a_successful_call(db_session: AsyncSession) -> None:
    incident = Incident(
        trigger="Checkout API returning 500s",
        evidence=["500s in logs"],
        status=IncidentStatus.DETECTED.value,
    )
    db_session.add(incident)
    await db_session.commit()

    fake_client = _fake_client(TRIAGE_RESULT, input_tokens=1000, output_tokens=200)
    with patch("app.agents.triage.get_anthropic_client", return_value=fake_client):
        result = await run_triage(incident, db_session, get_settings())

    assert result.status == IncidentStatus.TRIAGED.value

    spend = (await db_session.execute(select(DailySpend.total_cost_usd))).scalar_one()
    assert spend == calculate_cost("claude-sonnet-5", 1000, 200)


async def test_spend_is_recorded_after_a_failed_call_for_every_attempt(
    db_session: AsyncSession,
) -> None:
    incident = Incident(
        trigger="Checkout API returning 500s",
        evidence=["500s in logs"],
        status=IncidentStatus.DETECTED.value,
    )
    db_session.add(incident)
    await db_session.commit()

    # parsed_output=None on every attempt forces a ValidationError both times,
    # exhausting the one retry and escalating -- but each attempt still consumed
    # tokens and must still be counted.
    fake_client = _fake_client(None, input_tokens=1000, output_tokens=200)
    with patch("app.agents.triage.get_anthropic_client", return_value=fake_client):
        result = await run_triage(incident, db_session, get_settings())

    assert result.status == IncidentStatus.ESCALATED.value

    spend = (await db_session.execute(select(DailySpend.total_cost_usd))).scalar_one()
    assert spend == 2 * calculate_cost("claude-sonnet-5", 1000, 200)


async def test_anthropic_call_span_records_model_and_token_usage(
    db_session: AsyncSession, span_exporter: InMemorySpanExporter
) -> None:
    incident = Incident(
        trigger="Checkout API returning 500s",
        evidence=["500s in logs"],
        status=IncidentStatus.DETECTED.value,
    )
    db_session.add(incident)
    await db_session.commit()

    fake_client = _fake_client(TRIAGE_RESULT, input_tokens=1000, output_tokens=200)
    with patch("app.agents.triage.get_anthropic_client", return_value=fake_client):
        await run_triage(incident, db_session, get_settings())

    spans = [s for s in span_exporter.get_finished_spans() if s.name == "triage.anthropic_call"]
    assert len(spans) == 1
    attributes = spans[0].attributes
    assert attributes is not None
    assert attributes["gen_ai.request.model"] == "claude-sonnet-5"
    assert attributes["gen_ai.usage.input_tokens"] == 1000
    assert attributes["gen_ai.usage.output_tokens"] == 200
