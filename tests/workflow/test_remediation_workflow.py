from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.remediation import RemediationFailedError
from app.core.config import get_settings
from app.models.daily_spend import DailySpend
from app.models.incident import ActionType, Incident, IncidentStatus
from app.models.schemas import RemediationResult
from app.orchestration.remediation_workflow import run_remediation
from app.policies.pricing_policy import calculate_cost
from app.policies.remediation_policy import ACTION_RISK_LEVELS

REMEDIATION_RESULT = RemediationResult(
    action_type="restart_service",
    justification="connection pool exhaustion clears on restart",
    action_detail="restart checkout-api",
)


def _diagnosed_incident() -> Incident:
    return Incident(
        trigger="Checkout API returning 500s",
        evidence=["500s in logs", "connection pool at 0 available connections"],
        status=IncidentStatus.DIAGNOSED.value,
        severity="high",
        affected_service="checkout-api",
        symptoms=["elevated 500s"],
        root_cause="database connection pool exhaustion from a recent deploy",
        diagnosis_confidence="high",
    )


async def test_happy_path_transitions_diagnosed_to_validating(
    db_session: AsyncSession,
) -> None:
    incident = _diagnosed_incident()
    db_session.add(incident)
    await db_session.commit()

    with patch(
        "app.orchestration.remediation_workflow.call_remediation_agent_with_retry",
        AsyncMock(return_value=REMEDIATION_RESULT),
    ):
        result = await run_remediation(incident, db_session, get_settings())

    assert result.status == IncidentStatus.VALIDATING.value
    assert result.proposed_action_type == "restart_service"
    assert result.action_risk_level == "medium"
    assert result.action_justification == "connection pool exhaustion clears on restart"
    assert result.action_detail == "restart checkout-api"
    assert result.escalation_reason is None


async def test_failure_path_transitions_diagnosed_to_escalated(
    db_session: AsyncSession,
) -> None:
    incident = _diagnosed_incident()
    db_session.add(incident)
    await db_session.commit()

    with patch(
        "app.orchestration.remediation_workflow.call_remediation_agent_with_retry",
        AsyncMock(side_effect=RemediationFailedError("Remediation failed after retry: boom")),
    ):
        result = await run_remediation(incident, db_session, get_settings())

    assert result.status == IncidentStatus.ESCALATED.value
    assert result.proposed_action_type is None
    assert result.escalation_reason is not None
    assert "boom" in result.escalation_reason


@pytest.mark.parametrize("action_type", list(ActionType))
async def test_stored_risk_level_always_matches_the_fixed_policy_mapping(
    db_session: AsyncSession, action_type: ActionType
) -> None:
    incident = _diagnosed_incident()
    db_session.add(incident)
    await db_session.commit()

    result_for_action_type = RemediationResult(
        action_type=action_type,
        justification="justification text",
        action_detail="action detail text",
    )

    with patch(
        "app.orchestration.remediation_workflow.call_remediation_agent_with_retry",
        AsyncMock(return_value=result_for_action_type),
    ):
        result = await run_remediation(incident, db_session, get_settings())

    assert result.proposed_action_type == action_type.value
    assert result.action_risk_level == ACTION_RISK_LEVELS[action_type].value


async def test_spend_is_recorded_after_a_successful_call(db_session: AsyncSession) -> None:
    incident = _diagnosed_incident()
    db_session.add(incident)
    await db_session.commit()

    response = SimpleNamespace(
        parsed_output=REMEDIATION_RESULT,
        usage=SimpleNamespace(input_tokens=1000, output_tokens=200),
    )
    fake_client = Mock()
    fake_client.messages.parse = AsyncMock(return_value=response)
    with patch("app.agents.remediation.get_anthropic_client", return_value=fake_client):
        result = await run_remediation(incident, db_session, get_settings())

    assert result.status == IncidentStatus.VALIDATING.value

    spend = (await db_session.execute(select(DailySpend.total_cost_usd))).scalar_one()
    assert spend == calculate_cost("claude-sonnet-5", 1000, 200)


async def test_anthropic_call_span_records_model_and_token_usage(
    db_session: AsyncSession, span_exporter: InMemorySpanExporter
) -> None:
    incident = _diagnosed_incident()
    db_session.add(incident)
    await db_session.commit()

    response = SimpleNamespace(
        parsed_output=REMEDIATION_RESULT,
        usage=SimpleNamespace(input_tokens=1000, output_tokens=200),
    )
    fake_client = Mock()
    fake_client.messages.parse = AsyncMock(return_value=response)
    with patch("app.agents.remediation.get_anthropic_client", return_value=fake_client):
        await run_remediation(incident, db_session, get_settings())

    spans = [
        s for s in span_exporter.get_finished_spans() if s.name == "remediation.anthropic_call"
    ]
    assert len(spans) == 1
    attributes = spans[0].attributes
    assert attributes is not None
    assert attributes["gen_ai.request.model"] == "claude-sonnet-5"
    assert attributes["gen_ai.usage.input_tokens"] == 1000
    assert attributes["gen_ai.usage.output_tokens"] == 200
