from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.diagnosis import DiagnosisFailedError
from app.core.config import get_settings
from app.models.daily_spend import DailySpend
from app.models.incident import Incident, IncidentStatus
from app.models.schemas import DiagnosisResult
from app.orchestration.diagnosis_workflow import run_diagnosis
from app.policies.pricing_policy import calculate_cost

DIAGNOSIS_RESULT = DiagnosisResult(
    root_cause="database connection pool exhaustion from a recent deploy",
    evidence=["deploy v1.42.0 at 14:32 UTC"],
    confidence="high",
    alternative_explanations=["no plausible alternative explanations found"],
)


def _investigating_incident() -> Incident:
    return Incident(
        trigger="Checkout API returning 500s",
        evidence=["500s in logs"],
        status=IncidentStatus.INVESTIGATING.value,
        severity="high",
        affected_service="checkout-api",
        symptoms=["elevated 500s"],
        error_patterns=["connection pool exhausted"],
        deployment_correlation="deployed 8 min before onset",
        service_health_summary="elevated error rate and latency",
        investigation_confidence="high",
    )


async def test_happy_path_transitions_investigating_to_diagnosed(
    db_session: AsyncSession,
) -> None:
    incident = _investigating_incident()
    db_session.add(incident)
    await db_session.commit()

    with patch(
        "app.orchestration.diagnosis_workflow.call_diagnosis_agent_with_retry",
        AsyncMock(return_value=DIAGNOSIS_RESULT),
    ):
        result = await run_diagnosis(incident, db_session, get_settings())

    assert result.status == IncidentStatus.DIAGNOSED.value
    assert result.root_cause == "database connection pool exhaustion from a recent deploy"
    assert result.alternative_explanations == ["no plausible alternative explanations found"]
    assert result.diagnosis_confidence == "high"
    # original evidence is preserved, agent's evidence is appended, deduped
    assert result.evidence == ["500s in logs", "deploy v1.42.0 at 14:32 UTC"]
    assert result.escalation_reason is None


async def test_failure_path_transitions_investigating_to_escalated(
    db_session: AsyncSession,
) -> None:
    incident = _investigating_incident()
    db_session.add(incident)
    await db_session.commit()

    with patch(
        "app.orchestration.diagnosis_workflow.call_diagnosis_agent_with_retry",
        AsyncMock(side_effect=DiagnosisFailedError("Diagnosis failed after retry: boom")),
    ):
        result = await run_diagnosis(incident, db_session, get_settings())

    assert result.status == IncidentStatus.ESCALATED.value
    assert result.root_cause is None
    assert result.escalation_reason is not None
    assert "boom" in result.escalation_reason


async def test_evidence_dedupe_preserves_order(db_session: AsyncSession) -> None:
    incident = _investigating_incident()
    db_session.add(incident)
    await db_session.commit()

    duplicate_result = DiagnosisResult(
        root_cause="database connection pool exhaustion from a recent deploy",
        evidence=["500s in logs", "new evidence"],
        confidence="high",
        alternative_explanations=["no plausible alternative explanations found"],
    )

    with patch(
        "app.orchestration.diagnosis_workflow.call_diagnosis_agent_with_retry",
        AsyncMock(return_value=duplicate_result),
    ):
        result = await run_diagnosis(incident, db_session, get_settings())

    assert result.evidence == ["500s in logs", "new evidence"]


async def test_spend_is_recorded_after_a_successful_call(db_session: AsyncSession) -> None:
    incident = _investigating_incident()
    db_session.add(incident)
    await db_session.commit()

    response = SimpleNamespace(
        parsed_output=DIAGNOSIS_RESULT,
        usage=SimpleNamespace(input_tokens=1000, output_tokens=200),
    )
    fake_client = Mock()
    fake_client.messages.parse = AsyncMock(return_value=response)
    with patch("app.agents.diagnosis.get_anthropic_client", return_value=fake_client):
        result = await run_diagnosis(incident, db_session, get_settings())

    assert result.status == IncidentStatus.DIAGNOSED.value

    spend = (await db_session.execute(select(DailySpend.total_cost_usd))).scalar_one()
    assert spend == calculate_cost("claude-sonnet-5", 1000, 200)


async def test_anthropic_call_span_records_model_and_token_usage(
    db_session: AsyncSession, span_exporter: InMemorySpanExporter
) -> None:
    incident = _investigating_incident()
    db_session.add(incident)
    await db_session.commit()

    response = SimpleNamespace(
        parsed_output=DIAGNOSIS_RESULT,
        usage=SimpleNamespace(input_tokens=1000, output_tokens=200),
    )
    fake_client = Mock()
    fake_client.messages.parse = AsyncMock(return_value=response)
    with patch("app.agents.diagnosis.get_anthropic_client", return_value=fake_client):
        await run_diagnosis(incident, db_session, get_settings())

    spans = [s for s in span_exporter.get_finished_spans() if s.name == "diagnosis.anthropic_call"]
    assert len(spans) == 1
    attributes = spans[0].attributes
    assert attributes is not None
    assert attributes["gen_ai.request.model"] == "claude-sonnet-5"
    assert attributes["gen_ai.usage.input_tokens"] == 1000
    assert attributes["gen_ai.usage.output_tokens"] == 200
