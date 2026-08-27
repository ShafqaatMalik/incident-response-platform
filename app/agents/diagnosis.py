import anthropic
from pydantic import ValidationError

from app.core.anthropic_client import get_anthropic_client
from app.models.incident import Confidence, Incident, Severity
from app.models.schemas import DiagnosisContext, DiagnosisResult

DIAGNOSIS_SYSTEM_PROMPT = """\
You are the Diagnosis Agent in an AI incident response system.

You are given the incident's trigger, its Triage Agent output (severity,
affected service, symptoms), and its Investigation Agent output (error
patterns, deployment correlation, service health summary, investigation
confidence). Your job is ONLY to:
- state the most likely root cause, grounded in the evidence you were given
- cite the specific evidence (error patterns, deployment correlation,
  service health findings) that supports that root cause
- state your confidence in this diagnosis (low, medium, high)
- list alternative explanations you considered — if none are plausible
  given the evidence, say so explicitly (e.g. "no plausible alternative
  explanations found"); do not invent an alternative to fill the field

Do not propose a remediation or corrective action — that is a later
stage's job. Base your diagnosis only on the evidence given to you; do not
assume access to systems or evidence beyond what's provided. Every field
you return is required and must be non-empty: if you have nothing to add
in a category, say so explicitly rather than leaving it ambiguous or
inventing a finding.
"""


def build_diagnosis_context(
    incident: Incident,
    severity: Severity,
    affected_service: str,
    deployment_correlation: str,
    service_health_summary: str,
    investigation_confidence: Confidence,
) -> DiagnosisContext:
    """Pure, sync assembly — no I/O. `severity`/`affected_service`/
    `deployment_correlation`/`service_health_summary`/
    `investigation_confidence` are passed in already-narrowed (see
    run_diagnosis) rather than read off `incident` directly here: those
    columns are typed nullable at the ORM level, and an assert in the
    caller doesn't narrow that type inside this separate function — only
    within the caller's own scope. `symptoms`/`error_patterns` are read
    inline via `or []` since an empty-list fallback there doesn't mask a
    real None the way a blank string or missing enum value would.
    """
    return DiagnosisContext(
        trigger=incident.trigger,
        severity=severity,
        affected_service=affected_service,
        symptoms=list(incident.symptoms or []),
        error_patterns=list(incident.error_patterns or []),
        deployment_correlation=deployment_correlation,
        service_health_summary=service_health_summary,
        investigation_confidence=investigation_confidence,
    )


class DiagnosisFailedError(Exception):
    pass


async def _request_diagnosis(
    context: DiagnosisContext, model: str, *, repair_note: str | None = None
) -> DiagnosisResult:
    client = get_anthropic_client()
    prompt = context.model_dump_json()
    if repair_note:
        prompt += f"\n\nYour previous response was invalid: {repair_note}\nPlease correct it."

    try:
        response = await client.messages.parse(
            model=model,
            max_tokens=4096,
            system=DIAGNOSIS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
            output_format=DiagnosisResult,
        )
    except TypeError as exc:
        # See app/agents/triage.py's identical narrow catch for why this is
        # scoped to just this call — a missing-credentials failure surfaces
        # here as a bare TypeError, not an AnthropicError subclass.
        raise anthropic.AnthropicError(str(exc)) from exc

    if response.parsed_output is None:
        raise ValidationError.from_exception_data("DiagnosisResult", [])
    return response.parsed_output


async def call_diagnosis_agent_with_retry(context: DiagnosisContext, model: str) -> DiagnosisResult:
    """Exactly one retry/repair attempt, then escalate — per agent-rules.md.

    Catches anthropic.AnthropicError (the SDK's base exception, covering
    request-level failures like rate limits/timeouts, and — via
    _request_diagnosis's narrow re-raise — missing-credentials failures
    too) and pydantic.ValidationError (invalid output shape).
    """
    try:
        return await _request_diagnosis(context, model)
    except (anthropic.AnthropicError, ValidationError) as first_exc:
        try:
            return await _request_diagnosis(context, model, repair_note=str(first_exc))
        except (anthropic.AnthropicError, ValidationError) as second_exc:
            raise DiagnosisFailedError(
                f"Diagnosis failed after retry: {second_exc}"
            ) from second_exc
