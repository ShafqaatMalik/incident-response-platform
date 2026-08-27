import pytest

from app.models.incident import Incident, IncidentStatus
from app.orchestration.state_machine import InvalidTransitionError, transition, validate_transition


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


def test_triaged_to_investigating_is_allowed() -> None:
    incident = _incident(IncidentStatus.TRIAGED)
    transition(incident, IncidentStatus.INVESTIGATING)
    assert incident.status == IncidentStatus.INVESTIGATING.value


def test_triaged_to_escalated_is_allowed() -> None:
    incident = _incident(IncidentStatus.TRIAGED)
    transition(incident, IncidentStatus.ESCALATED)
    assert incident.status == IncidentStatus.ESCALATED.value


def test_investigating_to_diagnosed_is_allowed() -> None:
    incident = _incident(IncidentStatus.INVESTIGATING)
    transition(incident, IncidentStatus.DIAGNOSED)
    assert incident.status == IncidentStatus.DIAGNOSED.value


def test_investigating_to_escalated_is_allowed() -> None:
    incident = _incident(IncidentStatus.INVESTIGATING)
    transition(incident, IncidentStatus.ESCALATED)
    assert incident.status == IncidentStatus.ESCALATED.value


def test_diagnosed_to_validating_is_allowed() -> None:
    incident = _incident(IncidentStatus.DIAGNOSED)
    transition(incident, IncidentStatus.VALIDATING)
    assert incident.status == IncidentStatus.VALIDATING.value


def test_diagnosed_to_escalated_is_allowed() -> None:
    incident = _incident(IncidentStatus.DIAGNOSED)
    transition(incident, IncidentStatus.ESCALATED)
    assert incident.status == IncidentStatus.ESCALATED.value


def test_validating_to_awaiting_approval_is_allowed() -> None:
    incident = _incident(IncidentStatus.VALIDATING)
    transition(incident, IncidentStatus.AWAITING_APPROVAL)
    assert incident.status == IncidentStatus.AWAITING_APPROVAL.value


def test_validating_to_escalated_is_allowed() -> None:
    incident = _incident(IncidentStatus.VALIDATING)
    transition(incident, IncidentStatus.ESCALATED)
    assert incident.status == IncidentStatus.ESCALATED.value


def test_awaiting_approval_has_no_outgoing_transitions() -> None:
    incident = _incident(IncidentStatus.AWAITING_APPROVAL)
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


def test_validate_transition_raises_without_mutating() -> None:
    incident = _incident(IncidentStatus.DETECTED)
    with pytest.raises(InvalidTransitionError):
        validate_transition(incident, IncidentStatus.INVESTIGATING)
    assert incident.status == IncidentStatus.DETECTED.value


def test_validate_transition_does_not_mutate_on_success_either() -> None:
    incident = _incident(IncidentStatus.DETECTED)
    validate_transition(incident, IncidentStatus.TRIAGED)
    assert incident.status == IncidentStatus.DETECTED.value
