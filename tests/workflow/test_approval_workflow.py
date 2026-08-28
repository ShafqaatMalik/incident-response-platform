import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident, IncidentStatus
from app.orchestration.approval_workflow import run_approval, run_rejection
from app.orchestration.state_machine import InvalidTransitionError


def _awaiting_approval_incident(**overrides: object) -> Incident:
    defaults: dict[str, object] = {
        "trigger": "Checkout API returning 500s",
        "evidence": ["500s in logs"],
        "status": IncidentStatus.AWAITING_APPROVAL.value,
    }
    defaults.update(overrides)
    return Incident(**defaults)


async def test_happy_path_approve_transitions_to_approved(db_session: AsyncSession) -> None:
    incident = _awaiting_approval_incident()
    db_session.add(incident)
    await db_session.commit()

    result = await run_approval(incident, "on-call-engineer", db_session)

    assert result.status == IncidentStatus.APPROVED.value
    assert result.approved_by == "on-call-engineer"
    assert result.approved_at is not None


async def test_happy_path_reject_transitions_to_rejected(db_session: AsyncSession) -> None:
    incident = _awaiting_approval_incident()
    db_session.add(incident)
    await db_session.commit()

    result = await run_rejection(incident, "on-call-engineer", "insufficient evidence", db_session)

    assert result.status == IncidentStatus.REJECTED.value
    assert result.rejected_by == "on-call-engineer"
    assert result.rejected_at is not None
    assert result.rejection_reason == "insufficient evidence"


async def test_approve_when_not_awaiting_approval_raises(db_session: AsyncSession) -> None:
    incident = _awaiting_approval_incident(status=IncidentStatus.DIAGNOSED.value)
    db_session.add(incident)
    await db_session.commit()

    with pytest.raises(InvalidTransitionError):
        await run_approval(incident, "on-call-engineer", db_session)


async def test_reject_after_approve_raises(db_session: AsyncSession) -> None:
    incident = _awaiting_approval_incident()
    db_session.add(incident)
    await db_session.commit()

    await run_approval(incident, "on-call-engineer", db_session)

    with pytest.raises(InvalidTransitionError):
        await run_rejection(incident, "on-call-engineer", "changed my mind", db_session)
