# Incident Response Platform — Claude Code Guide

AI-assisted incident response system: a monitored FastAPI service on Cloud
Run, triaged/investigated/diagnosed by Claude agents through an explicit
state machine, with a mandatory human approval gate before any risky action
executes. Full design: `ARCHITECTURE.md`. Day-to-day log: `STATUS.md`.

## Current phase

Step 3 of the Build Order (`ARCHITECTURE.md` §20) is **done**: all four
agents plus the Validator now exist. Step 4 (production controls —
"Pydantic validation, guardrails, permissions, retries, fallbacks, human
approval" per §20) is **done**: human approval, the budget circuit
breaker (§7), and the decision to skip the fallback-model feature (logged
in `STATUS.md`) are all in place. The still-deferred agent retry-wrapper
refactor and the `get_incident_or_404`/budget-check-duplication refactors
are flagged cleanup opportunities, not blockers. Step 5 ("Deploy" — Cloud
Run, real/synthetic traffic, monitoring, failure injection, per §20) is
now **done** too: the app is live on Cloud Run, distributed tracing
exports to Google Cloud Trace, a Cloud Run Job sends realistic synthetic
traffic on a schedule, and a capped internal endpoint injects realistic
failures as real incidents. Real execution of an approved remediation
action was never part of §20's step 5 list and is **still not built** —
the state machine's terminal states remain `APPROVED`/`REJECTED`/
`ESCALATED` only; don't assume an execution path exists.

- Done: step 1 (service & architecture) and step 2 (non-AI FastAPI
  foundation — auth, rate limiting, logging, metrics, Docker, tests,
  CI/CD), commit `736ad9d`.
- Done: Triage Agent and the first real state transition
  (`DETECTED` → `TRIAGED`/`ESCALATED`) — agent, state machine, workflow,
  `Incident` model, `/internal/incidents` endpoints, full test pyramid
  (unit/integration/workflow/evaluation), CI `workflow` job.
- Done: Investigation Agent and `TRIAGED` → `INVESTIGATING`/`ESCALATED`
  — agent, workflow, `app/tools/` stubs (logs/deployments/metrics),
  `/internal/incidents/{id}/investigate`, full test pyramid.
- Done: Diagnosis Agent and `INVESTIGATING` → `DIAGNOSED`/`ESCALATED` —
  agent, workflow, `/internal/incidents/{id}/diagnose`, full test pyramid.
- Done: Remediation Agent and `DIAGNOSED` → `VALIDATING`/`ESCALATED`
  — agent, workflow, `app/policies/remediation_policy.py` (fixed
  action-type → risk-level mapping), `/internal/incidents/{id}/remediate`,
  full test pyramid.
- Done: the Validator and `VALIDATING` → `AWAITING_APPROVAL`/`ESCALATED`
  — a code-level check, not an agent: `app/policies/validation_policy.py`
  (fixed 6-rule set), `app/orchestration/validation_workflow.py`,
  `/internal/incidents/{id}/validate`, full test pyramid (no evaluation
  tier — no LLM call to evaluate). No new migration — reads only fields
  already on `Incident`. All four agents + the Validator now exist.
- Done: human approval — `AWAITING_APPROVAL` → `APPROVED`/`REJECTED`
  (both terminal for now, no execution yet) — `app/orchestration/
  approval_workflow.py`, `/internal/incidents/{id}/approve` (needs
  `approved_by`), `/internal/incidents/{id}/reject` (needs `rejected_by`
  + non-empty `rejection_reason`, 422 if missing), full test pyramid (no
  evaluation tier — no LLM call). Migration `0006` adds `approved_by`,
  `approved_at`, `rejected_by`, `rejected_at`, `rejection_reason`.
- Done: the budget circuit breaker — daily AI spend tracked in a new
  `daily_spend` table (migration `0007`), a fixed per-model pricing
  table (`app/policies/pricing_policy.py`, verified against Anthropic's
  published pricing), and a DB-backed check (`app/policies/
  budget_policy.py`) that blocks `/triage`, `/investigate`, `/diagnose`,
  `/remediate` with `429 budget_exceeded` once today's spend reaches
  `daily_budget_limit_usd` (default $2.00, configurable via `.env`).
  Incident creation and the Validator/approve/reject endpoints are
  unaffected — they make no AI call. Spend is recorded inside each
  agent's retry logic (every attempt, success or failure); the block
  check lives in the workflow layer instead, to keep the four agents'
  existing DB-free unit tests DB-free. Full test pyramid (no evaluation
  tier — no live LLM call).
- Done: Cloud Run deployment — live service in `australia-southeast1`
  (matching Supabase's region), secrets via Google Secret Manager, a
  dedicated least-privilege service account, database via Supabase's
  Transaction Pooler (switched from a direct connection after it proved
  unreachable from Cloud Run's egress). `Dockerfile` runs `tini` as
  `ENTRYPOINT` so the container actually honors Cloud Run's `SIGTERM`
  on scale-down/revision-swap — bare `uvicorn` as PID 1 doesn't.
- Done: OpenTelemetry tracing → Google Cloud Trace — FastAPI/SQLAlchemy
  auto-instrumented, manual spans around each agent's Anthropic call
  (model + token counts as attributes). Gated behind
  `otel_traces_enabled` (default off); the manual spans themselves are
  unconditional but are cheap no-ops when no exporter is configured, so
  nothing about tracing risks local dev or tests.
- Done: synthetic traffic — `scripts/synthetic_traffic/`, a standalone
  stdlib-only script (no new dependency on the main app), deployed as a
  Cloud Run Job triggered by Cloud Scheduler every 7 minutes, posting
  varied realistic text to `/documents`.
- Done: failure injection — `POST /internal/failures/inject`, three
  categories (`dependency_timeout`, `elevated_error_rate`,
  `latency_spike`), each producing a real `DETECTED` incident with
  category-specific realistic trigger text. Capped at
  `daily_failure_injection_limit` (default 5/day, new `daily_injections`
  table, migration `0008`) — `429 injection_cap_exceeded` once hit.
  Injected incidents are indistinguishable from manually-created ones
  and require the normal `/triage` → ... pipeline calls to progress,
  same as any other incident.
- Next: step 6 ("Evaluation") is the next Build Order step — the
  ~15–20 case incident dataset, automated evals, cost/latency
  measurement, run nightly rather than per-PR (per §11/§13). Not
  started; confirm scope first.

Don't jump ahead to step 6 or later steps without confirming scope first.

## Rules

@.claude/rules/architecture.md
@.claude/rules/security.md
@.claude/rules/testing.md
@.claude/rules/agent-rules.md

## Ground rules for this repo

- Read `ARCHITECTURE.md` before proposing any structural change — it is
  the source of truth, this file is a pointer into it.
- Follow the Build Order in §20. Don't jump ahead (e.g. don't write agent
  code before the non-AI FastAPI foundation exists).
- Keep `STATUS.md` in mind for what's already decided (hosting, DB,
  budget) — don't re-litigate those choices without being asked.
- Dev/test commands: `docker compose up -d` (Postgres + app),
  `uv run alembic upgrade head` (migrations), `uv run pytest` (runs
  unit + integration + workflow; the evaluation tier is excluded by
  default — run it separately with `uv run pytest -m evaluation`, real
  LLM calls, costs money), `uv run ruff check .` / `ruff format --check .`
  / `mypy app`. The app is deployed and live on Cloud Run
  (`australia-southeast1`); redeploys follow the same
  `gcloud builds submit` → `gcloud run deploy`/`services update`
  sequence logged in `STATUS.md`'s deploy entries, always **user-run**
  — `.claude/settings.json` denies Claude Code's own Bash tool from
  running `gcloud run deploy` and related commands regardless of
  approval.
