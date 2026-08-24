# AI Incident Triage & Resolution Platform — Architecture

## 1. Project Goal

Build a small, genuinely deployed production-like system that demonstrates
AI agents safely investigating and responding to real software incidents.

Flow: **detect → triage → investigate → diagnose → propose remediation →
validate → human approval → execute → verify → resolve/escalate**

This is **not** an autonomous system that fixes production on its own. It is
a demonstration of AI agents integrated into a safe, observable, testable
software workflow, with a human always in control of any risky action.

**Portfolio positioning:** "I built a production-oriented multi-agent
incident response system that investigates real service failures, validates
AI recommendations, requires human approval for risky actions, and verifies
recovery — with testing, observability, guardrails, CI/CD, and cost
controls."

The message: "I can engineer an AI system that behaves safely and predictably when things go wrong."


---

## 2. The Real System Being Monitored

A small public FastAPI service — e.g. a document/text processing API —
deployed continuously on Google Cloud Run.

Includes: authentication, request validation, rate limiting, structured
responses, logging, metrics, error handling, health checks, Docker, CI/CD.

Traffic sources:
- **Automated traffic** — a lightweight scheduled script sending realistic
  requests continuously
- **Deliberate failure injection** — controlled, internal-only triggers for
  500 errors, slow responses, dependency timeouts, malformed responses,
  failed deployments, temporary DB failures
- **Real usage** (optional, V2) — you and a small group of people, not the
  general public

Real requests → real failures → real logs → real incidents. No need for
volume.

---

## 3. Primary User

**Software/DevOps engineer** (initially: you), using an incident dashboard to:
view incidents, inspect evidence, review AI diagnosis, see proposed
remediation, approve/reject actions, request further investigation, manually
resolve or escalate.

The AI assists the engineer. It never replaces the final decision on
anything risky.

---

## 4. Multi-Agent System (4 agents + 1 validator, maximum)

1. **Triage Agent** — severity, affected service, symptoms, initial evidence
2. **Investigation Agent** — collects/analyzes logs, error patterns,
   latency, recent deployments, service health
3. **Diagnosis Agent** — likely root cause, supporting evidence, confidence,
   alternative explanations
4. **Remediation Agent** — proposes a safe corrective action; never executes
   high-risk actions automatically
5. **Validator** (not a conversational agent — a code-level check) —
   confirms the recommendation is evidence-supported, the action is
   allowed, the output is structurally valid, and whether human approval is
   required

**Orchestration:** built on the **Claude Agent SDK** (not LangGraph — this
is a deliberate choice to differentiate from the existing LangGraph RAG
portfolio project, and to directly demonstrate the harness concepts below).

**Workflow shape:** an explicit **state machine**. Agents do not freely
message each other — each step reads defined inputs, writes defined
outputs, and the state machine decides what happens next.

---

## 5. Incident Lifecycle (states)

```
DETECTED → TRIAGED → INVESTIGATING → DIAGNOSED →
AWAITING_APPROVAL → APPROVED / REJECTED →
EXECUTING → VERIFYING → RESOLVED / ESCALATED
```

### Incident record (core fields)
- id, created_at, status (one of the states above)
- trigger (which error/endpoint/signal)
- severity (low / medium / high / critical)
- evidence collected so far (logs, metrics snippets)
- diagnosis (cause, confidence, alternatives considered)
- proposed remediation
- approval decision (who, when, approve/reject)
- execution result
- verification result (did it actually fix it)

---

## 6. Production Safety Rules

AI agents cannot: delete data, expose secrets, modify arbitrary
infrastructure, execute dangerous commands, or make unrestricted production
changes.

High-risk actions always require: **AI recommendation → validation → human
approval → execution.**

Permissions are enforced at the application/tool layer (code), never by
prompt instructions alone.

Failure injection is gated behind an internal-only trigger — never
something a real visitor could stumble into and mistake for a real outage.

---

## 7. Failure Handling (a core feature, not an afterthought)

- **LLM failure:** timeout → retry → fallback model → human escalation
- **Invalid AI output:** Pydantic validation fails → retry/repair → escalate
  if still invalid
- **Tool failure:** logs unavailable → retry → timeout → fallback evidence
  → continue with reduced confidence, clearly marked
- **Conflicting diagnosis:** insufficient confidence → human review
- **Failed remediation:** service still unhealthy after execution →
  retry/rollback → escalation
- **Excessive cost/retries:** retry limit reached → stop workflow → record
  failure → human escalation

**Rule: the system must never silently fail or pretend an unsuccessful
action succeeded.** Every dead end surfaces as "escalated," never as
silently "done."

**Budget circuit breaker (in addition to the above):** track cumulative
daily AI spend; if a threshold is crossed, stop processing new incidents
and escalate, independent of any single workflow's retry logic.

**Injection rate cap:** synthetic failures are triggered on a capped
schedule (e.g. a few per day), not continuously — this is what keeps AI
spend predictable.

---

## 8. Context Management

Agents do **not** receive full incident history on every call. The system
maintains separate, purpose-scoped context: incident state, relevant
evidence, logs, metrics, deployment info, prior investigation results,
policies, and agent outputs. Only what a given step needs is passed in.
This is a deliberate cost-control and correctness measure, not just an
implementation detail — call it out as such in the portfolio writeup.

---

## 9. Schemas & Validation

Pydantic used throughout. Core schemas: `Incident`, `Evidence`, `Diagnosis`,
`RemediationProposal`, `Approval`, `ExecutionResult`, `VerificationResult`,
`AgentResponse`.

**No raw/untrusted LLM output ever directly triggers an action.** Every AI
response crossing an application boundary is validated first.

---

## 10. Observability

Every incident has a complete, inspectable trace: request latency, agent
latency, token usage, estimated AI cost, tool calls, failures, retries,
validation errors, human approvals/rejections, remediation success rate,
escalation rate.

**Implementation:** instrument the code properly with OpenTelemetry, but
export to **Google Cloud Logging/Trace** (already free-tier, already in use
for other projects) rather than standing up and hosting a separate
observability stack (Tempo/Jaeger/Grafana). Same end result — a hiring
manager can see exactly what happened at every stage — without the
self-hosting cost/complexity.

**Also track:** deployment metadata. Each Cloud Run revision is explicitly
tagged/logged with a timestamp, so the Investigation Agent has something
real to correlate errors against.

---

## 11. Evaluation

A small, realistic incident dataset (~15–20 cases): API failures, database
problems, deployment failures, auth failures, latency problems, dependency
failures.

Measure: diagnosis accuracy, severity accuracy, evidence quality,
remediation accuracy, hallucination/unsupported-claim rate, unsafe-action
rate, escalation accuracy, latency, cost per incident.

**Runs nightly**, not on every PR — see CI/CD below.

The project shows actual numbers, not "the agent works."

---

## 12. Testing

- **Unit tests** — functions, validators, policies, tools, services
- **Integration tests** — API↔database, API↔agents, agents↔tools,
  workflow↔execution
- **Workflow tests** — full scenarios (incident → investigation →
  diagnosis → approval → remediation → verification), with LLM calls
  **mocked** so these stay fast, free, and deterministic
- **Failure tests** — LLM timeout, invalid output, tool timeout, missing
  data, conflicting evidence, failed remediation, retry limits
- **Evaluation tests** — the real incident dataset run against live models,
  tracked over time (this is the one that costs money and runs nightly)

---

## 13. CI/CD

```
Pull Request
  → Lint
  → Unit Tests
  → Integration Tests
  → Workflow Tests (mocked LLM)
  → Security Checks
  → Docker Build
  → Deploy
```

Separately, on a **nightly schedule** (not per-PR): the real evaluation
suite against live models, with results tracked release-over-release.

This split is intentional: every PR is gated by fast, free, deterministic
checks; the AI evaluation cost is incurred once a day, not once per commit.

---

## 14. Claude Code / Agent Harness

Claude Code is the development agent for building this project.

```
CLAUDE.md

.claude/
├── rules/
│   ├── architecture.md
│   ├── security.md
│   ├── testing.md
│   └── agent-rules.md
│
├── skills/
│   ├── testing/
│   ├── observability/
│   ├── deployment/
│   └── incident-analysis/
│
└── settings.json
```

- Permissions restrict dangerous development actions
- Hooks used only where they add genuine value (e.g. automated checks
  before commit)
- MCP used only where it represents a real external tool boundary, not
  added for demonstration's sake

---

## 15. Deployment Stack

| Layer | Choice |
|---|---|
| Application | FastAPI + Python |
| Container | Docker |
| Cloud | Google Cloud Run |
| Database | **Supabase** (Postgres) — not Cloud SQL, which has no meaningful free tier |
| CI/CD | GitHub Actions |
| Frontend | Small React/TypeScript dashboard |
| Monitoring | OTel instrumentation → Google Cloud Logging/Trace |
| Agent orchestration | Claude Agent SDK |

Scales up under load, stays near-free when idle (Cloud Run scale-to-zero).

---

## 16. Budget

**Target: $20–28/month total, hard ceiling $30/month.**

| Item | Target |
|---|---:|
| Claude Code Pro | $20 |
| AI inference (Agent SDK usage) | $0–5 |
| Cloud Run | $0–3 |
| Supabase | $0 |
| Monitoring (Cloud Logging/Trace) | $0 |
| CI/CD (GitHub Actions) | $0 |

Cost control mechanisms baked into the design (not optional extras):
short/scoped context per agent call, cheap-model routing where reasoning
depth isn't needed, strict retry limits, a daily spend circuit breaker, and
a capped rate of synthetic failure injection.


---

## 17. Repository Structure

```
ai-incident-response/
│
├── app/
│   ├── api/
│   ├── agents/
│   ├── orchestration/
│   ├── tools/
│   ├── models/
│   ├── policies/
│   ├── services/
│   └── observability/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── workflow/
│   └── evaluation/
│
├── evals/
├── migrations/
├── frontend/
│
├── .github/
│   └── workflows/
│
├── .claude/
├── CLAUDE.md
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

---

## 18. Scope: V1 vs V2

**V1 — must ship:**
Real service (auth, validation, rate limiting, health checks) on Cloud Run;
Supabase Postgres; all 4 agents + Validator; Pydantic schemas on every AI
output boundary; human approval gate before any remediation executes; basic
dashboard (incident list, incident detail/evidence, approve/reject);
structured logs + OTel instrumentation exported to Cloud Logging/Trace;
unit + integration + mocked-workflow tests gating every PR; ~15–20 case
eval set run nightly; cost/latency tracked per incident; a daily budget
circuit breaker; the two-scenario demo (one clean resolution, one that
fails and escalates).

**V2 — only if V1 is solid and time remains:**
Full self-hosted observability backend; opening the service to real outside
users; richer failure-injection variety; dashboard visual polish.

---

## 19. Final Demo (what to actually show)

Note: "look, four agents talking to each other."

Instead, walk through **one complete incident, start to finish**: real
traffic → error spike → incident created → triage → investigation →
diagnosis → remediation proposal → validation → human approval requested →
approved → executed → verified → resolved.

Then a **second incident that fails partway**: tool timeout → retry →
fallback → insufficient evidence → human escalation. This second scenario
is not optional — it's the part that proves the system fails safely instead
of just working when everything goes right.

---

## 20. Build Order

1. **Define the real service & architecture** — API, database, incident
   model, workflow states, failure model
2. **Non-AI foundation** — FastAPI, auth, logging, metrics, Docker, tests,
   CI/CD
3. **Add the agents** — triage, investigation, diagnosis, remediation
4. **Production controls** — Pydantic validation, guardrails, permissions,
   retries, fallbacks, human approval
5. **Deploy** — Cloud Run, real/synthetic traffic, monitoring, failure
   injection
6. **Evaluation** — incident dataset, automated evals, cost/latency
   measurement
7. **Frontend** — incident dashboard, evidence view, approval flow,
   execution status
8. **Portfolio polish** — architecture diagram, failure demonstrations,
   evaluation results, cost numbers, short demo video, strong README
