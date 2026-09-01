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
are flagged cleanup opportunities, not blockers. Failure injection and
real execution of an approved action are step 5 ("Deploy"), not step 4 —
not started; confirm scope before beginning step 5.

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
- Next: step 5 ("Deploy") is the next Build Order step — Cloud Run,
  real/synthetic traffic, monitoring, failure injection, and real
  execution of an approved action. Not started; confirm scope first.

Don't jump ahead to step 5 or later steps without confirming scope first.

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
  / `mypy app`. No deploy command yet — Cloud Run deploy is Build Order
  step 5.
