import json
from typing import Literal

import anthropic
from pydantic import BaseModel, Field, ValidationError
from scenarios import Scenario

from app.core.anthropic_client import get_anthropic_client
from app.models.incident import Incident
from app.observability.tracing import anthropic_call_span

JUDGE_SYSTEM_PROMPT = """\
You are the evaluation judge for an AI incident response system. You are
given one test scenario's expected outcome and the actual outcome the
system produced, and must grade how well the actual outcome matches.

Grade four dimensions:
- severity_verdict: does the actual severity match the expected severity
  (or a reasonable, defensible judgment call)?
- diagnosis_verdict: does the actual root cause roughly match the
  expected root cause, OR — when the expected root cause is null — did
  the system correctly stay uncertain (escalate, or report low
  confidence) rather than confidently inventing a specific cause?
- remediation_verdict: does the actual proposed action match the intent
  of the expected proposed action? Use "not_applicable" if remediation
  was never reached (the incident escalated earlier) or if
  expected_proposed_action is null (the scenario expects escalation, not
  a remediation) — do not force a correct/reasonable/incorrect verdict
  onto a case with nothing to compare.
- hallucination_detected: does anything the system asserted (root cause,
  evidence, symptoms) go beyond what is actually supported by
  actual_evidence and the trigger text? Ground this check strictly in
  the given evidence — do not assume the system had access to any
  system, log, or fact it was not given.

For every verdict field, give required, specific reasoning — cite what
you compared, not just a label. If you find any unsupported claim, list
each one in unsupported_claims.
"""


class JudgeVerdict(BaseModel):
    severity_verdict: Literal["correct", "reasonable", "incorrect"]
    severity_reasoning: str
    diagnosis_verdict: Literal["correct", "reasonable", "incorrect"]
    diagnosis_reasoning: str
    remediation_verdict: Literal["correct", "reasonable", "incorrect", "not_applicable"]
    remediation_reasoning: str
    hallucination_detected: bool
    hallucination_reasoning: str
    unsupported_claims: list[str] = Field(default_factory=list)


def build_judge_prompt(scenario: Scenario, incident: Incident) -> str:
    payload = {
        "trigger": scenario.trigger,
        "expected_severity": scenario.expected.severity.value,
        "expected_root_cause": scenario.expected.root_cause,
        "expected_proposed_action": scenario.expected.proposed_action,
        "expected_notes": scenario.expected.notes,
        "actual_status": incident.status,
        "actual_severity": incident.severity,
        "actual_root_cause": incident.root_cause,
        "actual_diagnosis_confidence": incident.diagnosis_confidence,
        "actual_evidence": list(incident.evidence or []),
        "actual_escalation_reason": incident.escalation_reason,
        "actual_proposed_action_type": incident.proposed_action_type,
        "actual_action_detail": incident.action_detail,
        "actual_action_justification": incident.action_justification,
    }
    return json.dumps(payload, default=str)


class JudgeFailedError(Exception):
    pass


async def _request_judgment(
    scenario: Scenario, incident: Incident, model: str, *, repair_note: str | None = None
) -> JudgeVerdict:
    client = get_anthropic_client()
    prompt = build_judge_prompt(scenario, incident)
    if repair_note:
        prompt += f"\n\nYour previous response was invalid: {repair_note}\nPlease correct it."

    with anthropic_call_span("judge", model) as span:
        try:
            response = await client.messages.parse(
                model=model,
                max_tokens=4096,
                system=JUDGE_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
                output_format=JudgeVerdict,
            )
        except TypeError as exc:
            raise anthropic.AnthropicError(str(exc)) from exc

        span.set_attribute("gen_ai.usage.input_tokens", response.usage.input_tokens)
        span.set_attribute("gen_ai.usage.output_tokens", response.usage.output_tokens)

    if response.parsed_output is None:
        raise ValidationError.from_exception_data("JudgeVerdict", [])
    return response.parsed_output


async def call_judge_with_retry(
    scenario: Scenario, incident: Incident, model: str
) -> tuple[JudgeVerdict | None, str | None]:
    """One retry/repair attempt, then give up -- unlike the four agents, a
    failed judgment does not raise/crash the harness (there's no incident
    state to escalate); it's recorded as a per-scenario judge_error instead
    so one bad judge response doesn't lose the other scenarios' results."""
    try:
        return await _request_judgment(scenario, incident, model), None
    except (anthropic.AnthropicError, ValidationError) as first_exc:
        try:
            verdict = await _request_judgment(scenario, incident, model, repair_note=str(first_exc))
            return verdict, None
        except (anthropic.AnthropicError, ValidationError) as second_exc:
            return None, f"Judge failed after retry: {second_exc}"
