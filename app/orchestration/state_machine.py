from app.models.incident import Incident, IncidentStatus

ALLOWED_TRANSITIONS: dict[IncidentStatus, frozenset[IncidentStatus]] = {
    IncidentStatus.DETECTED: frozenset({IncidentStatus.TRIAGED, IncidentStatus.ESCALATED}),
    IncidentStatus.TRIAGED: frozenset(),
    IncidentStatus.ESCALATED: frozenset(),
}


class InvalidTransitionError(Exception):
    pass


def transition(incident: Incident, target: IncidentStatus) -> None:
    current = IncidentStatus(incident.status)
    if target not in ALLOWED_TRANSITIONS.get(current, frozenset()):
        raise InvalidTransitionError(
            f"{current.value} -> {target.value} is not an allowed transition"
        )
    incident.status = target.value
