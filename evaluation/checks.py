from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol

from scenarios import Scenario

from app.models.incident import ActionType, Incident, IncidentStatus
from app.policies.pricing_policy import calculate_cost
from app.policies.validation_policy import validate_remediation

_AGENT_STAGE_NAMES = frozenset({"triage", "investigation", "diagnosis", "remediation"})


@dataclass(frozen=True)
class CallRecord:
    stage: str
    model: str
    input_tokens: int
    output_tokens: int
    duration_ms: float


@dataclass(frozen=True)
class RuleBasedResult:
    final_status: str
    escalation_correct: bool
    valid_action_type: bool | None
    evidence_present_at_each_stage: bool
    validator_not_bypassed: bool
    cost_usd: Decimal
    judge_cost_usd: Decimal
    latency_ms_by_stage: dict[str, float] = field(default_factory=dict)


class _ReadableSpanLike(Protocol):
    name: str
    attributes: Any
    start_time: int
    end_time: int


def check_escalation_correctness(expected_should_escalate: bool, final_status: str) -> bool:
    return expected_should_escalate == (final_status == IncidentStatus.ESCALATED.value)


def check_valid_action_type(proposed_action_type: str | None) -> bool | None:
    if proposed_action_type is None:
        return None
    return proposed_action_type in {a.value for a in ActionType}


def check_evidence_present_at_each_stage(stage_evidence_counts: dict[str, int]) -> bool:
    return all(count > 0 for count in stage_evidence_counts.values())


def check_validator_not_bypassed(final_status: str, incident: Incident) -> bool:
    if final_status != IncidentStatus.AWAITING_APPROVAL.value:
        return True
    return validate_remediation(incident).passed


def extract_call_records(spans: list[_ReadableSpanLike]) -> list[CallRecord]:
    records = []
    for span in spans:
        if not span.name.endswith(".anthropic_call"):
            continue
        stage = span.name.removesuffix(".anthropic_call")
        attrs = span.attributes or {}
        records.append(
            CallRecord(
                stage=stage,
                model=str(attrs.get("gen_ai.request.model", "")),
                input_tokens=int(attrs.get("gen_ai.usage.input_tokens", 0)),
                output_tokens=int(attrs.get("gen_ai.usage.output_tokens", 0)),
                duration_ms=(span.end_time - span.start_time) / 1_000_000,
            )
        )
    return records


def cost_for_stage(records: list[CallRecord], stage: str) -> Decimal:
    return sum(
        (
            calculate_cost(r.model, r.input_tokens, r.output_tokens)
            for r in records
            if r.stage == stage
        ),
        Decimal("0"),
    )


def total_incident_cost(records: list[CallRecord]) -> Decimal:
    return sum(
        (
            calculate_cost(r.model, r.input_tokens, r.output_tokens)
            for r in records
            if r.stage in _AGENT_STAGE_NAMES
        ),
        Decimal("0"),
    )


def judge_cost(records: list[CallRecord]) -> Decimal:
    return cost_for_stage(records, "judge")


def latency_ms_by_stage(records: list[CallRecord]) -> dict[str, float]:
    result: dict[str, float] = {}
    for r in records:
        result[r.stage] = result.get(r.stage, 0.0) + r.duration_ms
    return result


def run_rule_based_checks(
    incident: Incident,
    scenario: Scenario,
    records: list[CallRecord],
    stage_evidence_counts: dict[str, int],
) -> RuleBasedResult:
    return RuleBasedResult(
        final_status=incident.status,
        escalation_correct=check_escalation_correctness(
            scenario.expected.should_escalate, incident.status
        ),
        valid_action_type=check_valid_action_type(incident.proposed_action_type),
        evidence_present_at_each_stage=check_evidence_present_at_each_stage(stage_evidence_counts),
        validator_not_bypassed=check_validator_not_bypassed(incident.status, incident),
        cost_usd=total_incident_cost(records),
        judge_cost_usd=judge_cost(records),
        latency_ms_by_stage=latency_ms_by_stage(records),
    )
