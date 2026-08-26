import pytest
from pydantic import ValidationError

from app.models.schemas import IncidentCreate, TriageContext, TriageResult


def test_incident_create_requires_trigger() -> None:
    with pytest.raises(ValidationError):
        IncidentCreate()  # type: ignore[call-arg]


def test_incident_create_rejects_empty_trigger() -> None:
    with pytest.raises(ValidationError):
        IncidentCreate(trigger="")


def test_incident_create_defaults_evidence_to_empty_list() -> None:
    incident = IncidentCreate(trigger="Service returning 500s")
    assert incident.initial_evidence == []


def test_triage_context_requires_all_fields() -> None:
    with pytest.raises(ValidationError):
        TriageContext()  # type: ignore[call-arg]


def test_triage_context_defaults_service_metadata() -> None:
    context = TriageContext(trigger="t", initial_evidence=[])
    assert context.service_metadata == {}


def test_triage_result_rejects_empty_symptoms() -> None:
    with pytest.raises(ValidationError):
        TriageResult(
            severity="high",
            affected_service="checkout-api",
            symptoms=[],
            initial_evidence=["500s in logs"],
        )


def test_triage_result_rejects_empty_evidence() -> None:
    with pytest.raises(ValidationError):
        TriageResult(
            severity="high",
            affected_service="checkout-api",
            symptoms=["elevated 500s"],
            initial_evidence=[],
        )


def test_triage_result_rejects_invalid_severity() -> None:
    with pytest.raises(ValidationError):
        TriageResult(
            severity="apocalyptic",
            affected_service="checkout-api",
            symptoms=["elevated 500s"],
            initial_evidence=["500s in logs"],
        )


def test_triage_result_accepts_valid_payload() -> None:
    result = TriageResult(
        severity="high",
        affected_service="checkout-api",
        symptoms=["elevated 500s", "latency spike"],
        initial_evidence=["500s in logs"],
    )
    assert result.severity.value == "high"
    assert result.affected_service == "checkout-api"
