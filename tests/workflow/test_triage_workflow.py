from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.triage import TriageFailedError
from app.core.config import get_settings
from app.models.incident import Incident, IncidentStatus
from app.models.schemas import TriageResult
from app.orchestration.triage_workflow import run_triage

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
