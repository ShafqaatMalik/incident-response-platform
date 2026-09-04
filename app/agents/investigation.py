import anthropic
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.anthropic_client import get_anthropic_client
from app.models.incident import Incident, Severity
from app.models.schemas import (
    DeploymentEvent,
    InvestigationContext,
    InvestigationResult,
    LogEntry,
    ServiceMetrics,
)
from app.observability.tracing import anthropic_call_span
from app.policies.budget_policy import record_spend

INVESTIGATION_SYSTEM_PROMPT = """\
You are the Investigation Agent in an AI incident response system.

You are given the incident's trigger, its Triage Agent output (severity,
affected service, symptoms), and evidence already fetched on your behalf
by the orchestration system: recent logs, deployment history, and service
metrics. Your job is ONLY to:
- identify error patterns in the fetched logs
- state whether any fetched deployment correlates with the incident's
  timing — if none does, say so explicitly (e.g. "no correlated
  deployment found"); do not invent a correlation to fill the field
- summarize the fetched service health (metrics)
- state your confidence in these findings (low, medium, high)
- cite the specific evidence (log lines, deployment entries, metric
  values) that supports your findings

Do not propose a root cause, diagnosis, or remediation — those are later
stages' jobs. Base your assessment only on the evidence given to you; do
not assume access to logs, metrics, or systems beyond what's provided.
Every field you return is required and must be non-empty: if you find
nothing anomalous in a category, say so explicitly (e.g. "no error
patterns found in the sampled logs") rather than leaving it ambiguous or
inventing a finding.
"""


def build_investigation_context(
    incident: Incident,
    severity: Severity,
    affected_service: str,
    logs: list[LogEntry],
    deployments: list[DeploymentEvent],
    metrics: ServiceMetrics,
) -> InvestigationContext:
    """Pure, sync assembly — no I/O. `severity`/`affected_service` are passed
    in already-narrowed (see run_investigation) rather than read off
    `incident` directly here: Incident.severity/affected_service are typed
    `str | None` at the ORM level, and an assert in the caller doesn't
    narrow that type inside this separate function — only within the
    caller's own scope.
    """
    return InvestigationContext(
        trigger=incident.trigger,
        severity=severity,
        affected_service=affected_service,
        symptoms=list(incident.symptoms or []),
        recent_logs=logs,
        deployment_history=deployments,
        service_metrics=metrics,
    )


class InvestigationFailedError(Exception):
    pass


async def _request_investigation(
    context: InvestigationContext,
    model: str,
    session: AsyncSession,
    *,
    repair_note: str | None = None,
) -> InvestigationResult:
    client = get_anthropic_client()
    prompt = context.model_dump_json()
    if repair_note:
        prompt += f"\n\nYour previous response was invalid: {repair_note}\nPlease correct it."

    with anthropic_call_span("investigation", model) as span:
        try:
            response = await client.messages.parse(
                model=model,
                max_tokens=4096,
                system=INVESTIGATION_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
                output_format=InvestigationResult,
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
        raise ValidationError.from_exception_data("InvestigationResult", [])
    return response.parsed_output


async def call_investigation_agent_with_retry(
    context: InvestigationContext, model: str, session: AsyncSession
) -> InvestigationResult:
    """Exactly one retry/repair attempt, then escalate — per agent-rules.md.

    Catches anthropic.AnthropicError (the SDK's base exception, covering
    request-level failures like rate limits/timeouts, and — via
    _request_investigation's narrow re-raise — missing-credentials
    failures too) and pydantic.ValidationError (invalid output shape).
    """
    try:
        return await _request_investigation(context, model, session)
    except (anthropic.AnthropicError, ValidationError) as first_exc:
        try:
            return await _request_investigation(context, model, session, repair_note=str(first_exc))
        except (anthropic.AnthropicError, ValidationError) as second_exc:
            raise InvestigationFailedError(
                f"Investigation failed after retry: {second_exc}"
            ) from second_exc
