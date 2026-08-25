# Architecture rules

Source of truth: `ARCHITECTURE.md` (this file is the enforceable summary).

## State machine, not free-form agent chat

The incident lifecycle is a fixed state machine:

DETECTED → TRIAGED → INVESTIGATING → DIAGNOSED → AWAITING_APPROVAL →
APPROVED / REJECTED → EXECUTING → VERIFYING → RESOLVED / ESCALATED

- Agents never call each other directly. Each step reads defined inputs,
  writes a defined output, and the state machine (code) decides the next
  transition.
- Every state transition must be explicit and logged. No implicit or
  inferred transitions.
- Do not add states, agents, or direct agent-to-agent messaging without
  updating `ARCHITECTURE.md` first — the code and the doc must stay in
  sync.

## Agents (4 + 1 validator — this is a ceiling, not a floor)

1. Triage Agent — severity, affected service, symptoms, initial evidence
2. Investigation Agent — logs, error patterns, latency, deployments,
   service health
3. Diagnosis Agent — root cause, evidence, confidence, alternatives
4. Remediation Agent — proposes safe corrective action; **never executes
   high-risk actions itself**
5. Validator — not a conversational agent, a code-level check: confirms
   evidence-support, permission, structural validity, and whether human
   approval is required

Do not merge agents' responsibilities or add a 6th agent to sidestep this
list — if the design needs to grow, that's a decision for the user, not an
implementation shortcut.

## Orchestration

- Built on the **Claude Agent SDK**. Do not introduce LangGraph or another
  orchestration framework — this is a deliberate portfolio differentiation
  choice, not an oversight.
- Orchestration logic (the state machine, transition rules, retry/fallback
  policy) lives in application code (`app/orchestration/`), not in prompts.

## Schemas & validation (non-negotiable)

- Every AI output that crosses an application boundary is a Pydantic
  model: `Incident`, `Evidence`, `Diagnosis`, `RemediationProposal`,
  `Approval`, `ExecutionResult`, `VerificationResult`, `AgentResponse`.
- **No raw/untrusted LLM output ever directly triggers an action.**
  Parse → validate → then act. If validation fails: retry/repair, then
  escalate if still invalid (see `agent-rules.md` and `security.md`).
- Don't loosen a schema (e.g. `Optional[Any]`, bypassing validation "just
  for now") to unblock a feature — fix the upstream data/prompt instead.

## Context management

Agents receive scoped, purpose-built context per call (relevant evidence,
policies, prior outputs for that step) — never the full incident history
by default. This is a cost-control *and* correctness measure; treat it as
a hard constraint on how context-building code is written, not an
optimization to defer.
