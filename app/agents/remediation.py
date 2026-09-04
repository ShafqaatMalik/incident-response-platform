import anthropic
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.anthropic_client import get_anthropic_client
from app.models.incident import Confidence, Incident
from app.models.schemas import RemediationContext, RemediationResult
from app.observability.tracing import anthropic_call_span
from app.policies.budget_policy import record_spend

REMEDIATION_SYSTEM_PROMPT = """\
You are the Remediation Agent in an AI incident response system.

You are given the incident's trigger, affected service, its Diagnosis
Agent output (root cause, confidence), and the evidence gathered so far.
Your job is ONLY to:
- choose exactly one action_type from this fixed list: restart_service,
  rollback_deployment, scale_up, disable_traffic, no_action_needed,
  manual_investigation_required
- justify that choice, grounded in the root cause and evidence you were
  given
- describe the action concretely in action_detail — name the specific
  service involved and what should happen to it

You do not decide how risky an action is — that is fixed by the system
for each action type, regardless of what you write. Never state or imply
a risk/severity level for the action yourself.

Choosing no_action_needed or manual_investigation_required is NOT an
exemption from writing a real, specific justification and action_detail —
a human will read both before approving anything, including these two.
Never write a placeholder like "n/a", "none", or "no action" alone.
- If you choose no_action_needed: action_detail must state, in your own
  assessment, why the incident does not need a corrective action (e.g.
  "error rate returned to baseline within the observed window; consistent
  with a transient spike, not an ongoing fault") — this still goes to a
  human for confirmation, not an automatic close, so write it as if you
  are the one recommending "close this" to that person.
- If you choose manual_investigation_required: action_detail must state
  specifically what is unclear or insufficient about the evidence you
  were given, and what a human investigator should look at first — not
  just "unclear, needs review."

Base your recommendation only on the evidence given to you; do not assume
access to systems beyond what's provided. Every field you return is
required and must be a real, specific statement — never an empty or
placeholder value.
"""


def build_remediation_context(
    incident: Incident,
    affected_service: str,
    root_cause: str,
    diagnosis_confidence: Confidence,
) -> RemediationContext:
    """Pure, sync assembly — no I/O. `affected_service`/`root_cause`/
    `diagnosis_confidence` are passed in already-narrowed (see
    run_remediation) rather than read off `incident` directly here: those
    columns are typed nullable at the ORM level, and an assert in the
    caller doesn't narrow that type inside this separate function — only
    within the caller's own scope. `evidence` is read directly since
    Incident.evidence is non-nullable (defaults to an empty list).
    """
    return RemediationContext(
        trigger=incident.trigger,
        affected_service=affected_service,
        root_cause=root_cause,
        diagnosis_confidence=diagnosis_confidence,
        evidence=list(incident.evidence),
    )


class RemediationFailedError(Exception):
    pass


async def _request_remediation(
    context: RemediationContext,
    model: str,
    session: AsyncSession,
    *,
    repair_note: str | None = None,
) -> RemediationResult:
    client = get_anthropic_client()
    prompt = context.model_dump_json()
    if repair_note:
        prompt += f"\n\nYour previous response was invalid: {repair_note}\nPlease correct it."

    with anthropic_call_span("remediation", model) as span:
        try:
            response = await client.messages.parse(
                model=model,
                max_tokens=4096,
                system=REMEDIATION_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
                output_format=RemediationResult,
            )
        except TypeError as exc:
            # See app/agents/triage.py's identical narrow catch for why this is
            # scoped to just this call — a missing-credentials failure surfaces
            # here as a bare TypeError, not an AnthropicError subclass.
            raise anthropic.AnthropicError(str(exc)) from exc

        span.set_attribute("gen_ai.usage.input_tokens", response.usage.input_tokens)
        span.set_attribute("gen_ai.usage.output_tokens", response.usage.output_tokens)

    await record_spend(session, model, response.usage.input_tokens, response.usage.output_tokens)

    if response.parsed_output is None:
        raise ValidationError.from_exception_data("RemediationResult", [])
    return response.parsed_output


async def call_remediation_agent_with_retry(
    context: RemediationContext, model: str, session: AsyncSession
) -> RemediationResult:
    """Exactly one retry/repair attempt, then escalate — per agent-rules.md.

    Catches anthropic.AnthropicError (the SDK's base exception, covering
    request-level failures like rate limits/timeouts, and — via
    _request_remediation's narrow re-raise — missing-credentials failures
    too) and pydantic.ValidationError (invalid output shape).
    """
    try:
        return await _request_remediation(context, model, session)
    except (anthropic.AnthropicError, ValidationError) as first_exc:
        try:
            return await _request_remediation(context, model, session, repair_note=str(first_exc))
        except (anthropic.AnthropicError, ValidationError) as second_exc:
            raise RemediationFailedError(
                f"Remediation failed after retry: {second_exc}"
            ) from second_exc
