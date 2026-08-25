# Agent behavior rules

Source of truth: `ARCHITECTURE.md` §7–8.

## Scoped context per call

Each agent call receives only what that step needs — never the full
incident history by default:
- Triage: trigger signal, initial evidence, service metadata
- Investigation: incident + triage output, relevant logs/metrics/deploy
  info, tool results
- Diagnosis: incident + investigation output, relevant policies
- Remediation: incident + diagnosis output, action policy/allowlist

When implementing an agent's context-builder, name explicitly what goes in
— don't pass a whole incident object "to be safe."

## Structured output only

- Every agent call returns a Pydantic-validated `AgentResponse` (or the
  relevant sub-schema: `Diagnosis`, `RemediationProposal`, etc.) — never a
  free-text string consumed downstream.
- The validator is the single place that checks: evidence-supported,
  action allowed, structurally valid, approval-required. Don't duplicate
  ad-hoc validation logic inside individual agents.

## Escalate, never silently fail

Every dead end becomes an explicit `ESCALATED` state, never a quiet
"done":
- LLM failure → timeout → retry → fallback model → escalate
- Invalid AI output → Pydantic fails → retry/repair → escalate if still
  invalid
- Tool failure (e.g. logs unavailable) → retry → timeout → fallback
  evidence, clearly marked as reduced-confidence → continue or escalate
- Conflicting diagnosis / low confidence → escalate to human review
- Failed remediation (still unhealthy post-execution) → retry/rollback →
  escalate
- Retry limit reached → stop workflow, record failure, escalate

When implementing any of the above, the escalation path is not an
afterthought — write the test for it (see `testing.md`) alongside the
happy path, not after.

## Cost discipline

- Route to a cheaper/faster model where reasoning depth isn't needed
  (e.g. structured extraction) — reserve the strongest model for
  diagnosis/remediation reasoning.
- Respect the daily budget circuit breaker: if implementing spend
  tracking, it must be able to halt new incident processing independent
  of any single workflow's own retry logic.
