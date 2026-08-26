from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.investigation import InvestigationFailedError
from app.core.config import get_settings
from app.models.incident import Incident, IncidentStatus
from app.models.schemas import InvestigationResult
from app.orchestration.investigation_workflow import run_investigation

INVESTIGATION_RESULT = InvestigationResult(
    error_patterns=["connection pool exhausted"],
    deployment_correlation="deployed 8 min before onset",
    service_health_summary="elevated error rate and latency",
    confidence="high",
    evidence=["deploy v1.42.0 at 14:32 UTC"],
)


def _triaged_incident() -> Incident:
    return Incident(
        trigger="Checkout API returning 500s",
        evidence=["500s in logs"],
        status=IncidentStatus.TRIAGED.value,
        severity="high",
        affected_service="checkout-api",
        symptoms=["elevated 500s"],
    )


async def test_happy_path_transitions_triaged_to_investigating(db_session: AsyncSession) -> None:
    incident = _triaged_incident()
    db_session.add(incident)
    await db_session.commit()

    with patch(
        "app.orchestration.investigation_workflow.call_investigation_agent_with_retry",
        AsyncMock(return_value=INVESTIGATION_RESULT),
    ):
        result = await run_investigation(incident, db_session, get_settings())

    assert result.status == IncidentStatus.INVESTIGATING.value
    assert result.error_patterns == ["connection pool exhausted"]
    assert result.deployment_correlation == "deployed 8 min before onset"
    assert result.service_health_summary == "elevated error rate and latency"
    assert result.investigation_confidence == "high"
    # original evidence is preserved, agent's evidence is appended, deduped
    assert result.evidence == ["500s in logs", "deploy v1.42.0 at 14:32 UTC"]
    assert result.escalation_reason is None


async def test_failure_path_transitions_triaged_to_escalated(db_session: AsyncSession) -> None:
    incident = _triaged_incident()
    db_session.add(incident)
    await db_session.commit()

    with patch(
        "app.orchestration.investigation_workflow.call_investigation_agent_with_retry",
        AsyncMock(side_effect=InvestigationFailedError("Investigation failed after retry: boom")),
    ):
        result = await run_investigation(incident, db_session, get_settings())

    assert result.status == IncidentStatus.ESCALATED.value
    assert result.error_patterns is None
    assert result.escalation_reason is not None
    assert "boom" in result.escalation_reason


async def test_evidence_dedupe_preserves_order(db_session: AsyncSession) -> None:
    incident = _triaged_incident()
    db_session.add(incident)
    await db_session.commit()

    duplicate_result = InvestigationResult(
        error_patterns=["connection pool exhausted"],
        deployment_correlation="deployed 8 min before onset",
        service_health_summary="elevated error rate and latency",
        confidence="high",
        evidence=["500s in logs", "new evidence"],
    )

    with patch(
        "app.orchestration.investigation_workflow.call_investigation_agent_with_retry",
        AsyncMock(return_value=duplicate_result),
    ):
        result = await run_investigation(incident, db_session, get_settings())

    assert result.evidence == ["500s in logs", "new evidence"]
