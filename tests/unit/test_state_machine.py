import pytest

from app.models.incident import Incident, IncidentStatus
from app.orchestration.state_machine import InvalidTransitionError, transition


def _incident(status: IncidentStatus) -> Incident:
    return Incident(trigger="t", evidence=[], status=status.value)


def test_detected_to_triaged_is_allowed() -> None:
    incident = _incident(IncidentStatus.DETECTED)
    transition(incident, IncidentStatus.TRIAGED)
    assert incident.status == IncidentStatus.TRIAGED.value


def test_detected_to_escalated_is_allowed() -> None:
    incident = _incident(IncidentStatus.DETECTED)
    transition(incident, IncidentStatus.ESCALATED)
    assert incident.status == IncidentStatus.ESCALATED.value


def test_triaged_has_no_outgoing_transitions() -> None:
    incident = _incident(IncidentStatus.TRIAGED)
    with pytest.raises(InvalidTransitionError):
        transition(incident, IncidentStatus.ESCALATED)


def test_escalated_has_no_outgoing_transitions() -> None:
    incident = _incident(IncidentStatus.ESCALATED)
    with pytest.raises(InvalidTransitionError):
        transition(incident, IncidentStatus.TRIAGED)


def test_cannot_transition_to_same_state() -> None:
    incident = _incident(IncidentStatus.DETECTED)
    with pytest.raises(InvalidTransitionError):
        transition(incident, IncidentStatus.DETECTED)
