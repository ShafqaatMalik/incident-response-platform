from app.models.incident import Incident, IncidentStatus

ALLOWED_TRANSITIONS: dict[IncidentStatus, frozenset[IncidentStatus]] = {
    IncidentStatus.DETECTED: frozenset({IncidentStatus.TRIAGED, IncidentStatus.ESCALATED}),
    IncidentStatus.TRIAGED: frozenset({IncidentStatus.INVESTIGATING, IncidentStatus.ESCALATED}),
    IncidentStatus.INVESTIGATING: frozenset({IncidentStatus.DIAGNOSED, IncidentStatus.ESCALATED}),
    IncidentStatus.DIAGNOSED: frozenset(
        {IncidentStatus.AWAITING_APPROVAL, IncidentStatus.ESCALATED}
    ),
    IncidentStatus.AWAITING_APPROVAL: frozenset(),
    IncidentStatus.ESCALATED: frozenset(),
}


class InvalidTransitionError(Exception):
    pass


def validate_transition(incident: Incident, target: IncidentStatus) -> None:
    current = IncidentStatus(incident.status)
    if target not in ALLOWED_TRANSITIONS.get(current, frozenset()):
        raise InvalidTransitionError(
            f"{current.value} -> {target.value} is not an allowed transition"
        )


def transition(incident: Incident, target: IncidentStatus) -> None:
    validate_transition(incident, target)
    incident.status = target.value
