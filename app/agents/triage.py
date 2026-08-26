import anthropic
from pydantic import ValidationError

from app.core.anthropic_client import get_anthropic_client
from app.core.config import Settings
from app.models.incident import Incident
from app.models.schemas import TriageContext, TriageResult

TRIAGE_SYSTEM_PROMPT = """\
You are the Triage Agent in an AI incident response system.

You are given a trigger description, whatever initial evidence is already
on the incident record, and static service metadata. Your job is ONLY to:
- assess severity (low, medium, high, critical)
- identify the affected service
- list the symptoms
- state the initial evidence that supports your assessment

Do not propose a diagnosis, root cause, or remediation — those are later
stages' jobs. Base your assessment only on the information given to you;
do not assume access to logs, metrics, or systems you have not been given.
"""


def build_triage_context(incident: Incident, settings: Settings) -> TriageContext:
    return TriageContext(
        trigger=incident.trigger,
        initial_evidence=list(incident.evidence or []),
        service_metadata={
            "service_name": "incident-response-platform-api",
            "environment": settings.environment,
        },
    )


class TriageFailedError(Exception):
    pass


async def _request_triage(
    context: TriageContext, model: str, *, repair_note: str | None = None
) -> TriageResult:
    client = get_anthropic_client()
    prompt = context.model_dump_json()
    if repair_note:
        prompt += f"\n\nYour previous response was invalid: {repair_note}\nPlease correct it."

    try:
        response = await client.messages.parse(
            model=model,
            max_tokens=4096,
            system=TRIAGE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
            output_format=TriageResult,
        )
    except TypeError as exc:
        # anthropic.AsyncAnthropic() doesn't validate credentials at construction
        # (see has_anthropic_credentials' docstring); a "no credentials resolved"
        # failure only surfaces here, as a bare TypeError, not an AnthropicError
        # subclass — confirmed empirically against anthropic==1.0.0. Narrowly
        # scoped to just this call so a genuine TypeError bug elsewhere in this
        # function (or in the retry logic below) isn't misreported as a triage
        # failure — it propagates unhandled instead.
        raise anthropic.AnthropicError(str(exc)) from exc

    if response.parsed_output is None:
        raise ValidationError.from_exception_data("TriageResult", [])
    return response.parsed_output


async def call_triage_agent_with_retry(context: TriageContext, model: str) -> TriageResult:
    """Exactly one retry/repair attempt, then escalate — per agent-rules.md.

    Catches anthropic.AnthropicError (the SDK's base exception, covering
    request-level failures like rate limits/timeouts, and — via
    _request_triage's narrow re-raise — missing-credentials failures too)
    and pydantic.ValidationError (invalid output shape).
    """
    try:
        return await _request_triage(context, model)
    except (anthropic.AnthropicError, ValidationError) as first_exc:
        try:
            return await _request_triage(context, model, repair_note=str(first_exc))
        except (anthropic.AnthropicError, ValidationError) as second_exc:
            raise TriageFailedError(f"Triage failed after retry: {second_exc}") from second_exc
