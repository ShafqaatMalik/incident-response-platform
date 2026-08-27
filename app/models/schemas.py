import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.incident import ActionType, Confidence, IncidentStatus, RiskLevel, Severity


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
    error_patterns: list[str] | None
    deployment_correlation: str | None
    service_health_summary: str | None
    investigation_confidence: Confidence | None
    root_cause: str | None
    alternative_explanations: list[str] | None
    diagnosis_confidence: Confidence | None
    proposed_action_type: ActionType | None
    action_risk_level: RiskLevel | None
    action_justification: str | None
    action_detail: str | None

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


class LogEntry(BaseModel):
    """Shape returned by app/tools/logs.py's get_recent_logs()."""

    timestamp: datetime
    level: str
    message: str


class DeploymentEvent(BaseModel):
    """Shape returned by app/tools/deployments.py's get_deployment_history()."""

    timestamp: datetime
    version: str
    description: str


class ServiceMetrics(BaseModel):
    """Shape returned by app/tools/metrics.py's get_service_metrics()."""

    error_rate: float
    p99_latency_ms: float
    cpu_utilization: float


class InvestigationContext(BaseModel):
    """Scoped agent input — incident's triage output plus orchestration-fetched
    evidence, never the full Incident row or its history."""

    trigger: str
    severity: Severity
    affected_service: str
    symptoms: list[str]
    recent_logs: list[LogEntry]
    deployment_history: list[DeploymentEvent]
    service_metrics: ServiceMetrics


class InvestigationResult(BaseModel):
    """The Investigation Agent's validated output. Exactly ARCHITECTURE.md §4's
    Investigation Agent fields — no free-text root-cause reasoning (that's
    Diagnosis's job). Every field is required and non-empty: the agent must
    state findings explicitly, e.g. "no correlated deployment found" or "no
    error patterns found in the sampled logs", rather than leaving a field
    ambiguously unset or hallucinating a finding to satisfy validation."""

    error_patterns: list[str] = Field(min_length=1)
    deployment_correlation: str = Field(min_length=1)
    service_health_summary: str = Field(min_length=1)
    confidence: Confidence
    evidence: list[str] = Field(min_length=1)


class DiagnosisContext(BaseModel):
    """Scoped agent input — incident's triage + investigation output, never
    the full Incident row or its history."""

    trigger: str
    severity: Severity
    affected_service: str
    symptoms: list[str]
    error_patterns: list[str]
    deployment_correlation: str
    service_health_summary: str
    investigation_confidence: Confidence


class DiagnosisResult(BaseModel):
    """The Diagnosis Agent's validated output. Exactly ARCHITECTURE.md
    §4/§5's Diagnosis Agent fields — no free-text remediation proposal
    (that's the Remediation Agent's job). `evidence` (not
    `supporting_evidence`) to match the merge-into-`incident.evidence`
    convention already used by Triage's `initial_evidence` and
    Investigation's `evidence`. Every field is required and non-empty: the
    agent must state findings explicitly, e.g. "no plausible alternative
    explanations found", rather than leaving a field ambiguously unset."""

    root_cause: str = Field(min_length=1)
    evidence: list[str] = Field(min_length=1)
    confidence: Confidence
    alternative_explanations: list[str] = Field(min_length=1)


class RemediationContext(BaseModel):
    """Scoped agent input — incident + diagnosis output only, per
    agent-rules.md (narrower than Diagnosis's own context, which carried
    forward both Triage's and Investigation's output)."""

    trigger: str
    affected_service: str
    root_cause: str
    diagnosis_confidence: Confidence
    evidence: list[str]


class RemediationResult(BaseModel):
    """The Remediation Agent's validated output. `action_type` must be one
    of the six fixed ActionType values — the agent picks WHICH action
    applies and describes it concretely, but never decides how risky that
    action type is; risk level is a fixed code-level mapping applied by
    the workflow (app/policies/remediation_policy.py), not a field here at
    all. Every field required and non-empty, including for
    no_action_needed/manual_investigation_required — the agent must still
    justify the choice and describe what it means concretely (e.g. "no
    corrective action needed: symptoms consistent with a resolved
    transient spike" or "insufficient evidence to propose a specific
    action; escalate to on-call for manual review")."""

    action_type: ActionType
    justification: str = Field(min_length=1)
    action_detail: str = Field(min_length=1)
