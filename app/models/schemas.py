import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.incident import IncidentStatus, Severity


class DocumentCreate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    text: str = Field(min_length=1, max_length=50_000)


class DocumentResponse(BaseModel):
    id: uuid.UUID
    title: str | None
    source_text: str
    summary: str
    word_count: int
    sentence_count: int
    readability_score: float
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    limit: int
    offset: int


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class IncidentCreate(BaseModel):
    trigger: str = Field(min_length=1, max_length=2000)
    initial_evidence: list[str] = Field(default_factory=list)


class IncidentResponse(BaseModel):
    id: uuid.UUID
    created_at: datetime
    status: IncidentStatus
    trigger: str
    severity: Severity | None
    affected_service: str | None
    symptoms: list[str] | None
    evidence: list[str]
    escalation_reason: str | None

    model_config = {"from_attributes": True}


class TriageContext(BaseModel):
    """Scoped agent input — never the full Incident row or its history."""

    trigger: str
    initial_evidence: list[str]
    service_metadata: dict[str, str] = Field(default_factory=dict)


class TriageResult(BaseModel):
    """The Triage Agent's validated output. Exactly ARCHITECTURE.md §4's
    Triage Agent fields — no free-text reasoning blob."""

    severity: Severity
    affected_service: str = Field(min_length=1, max_length=255)
    symptoms: list[str] = Field(min_length=1)
    initial_evidence: list[str] = Field(min_length=1)
