# Incident Response Platform — Claude Code Guide

AI-assisted incident response system: a monitored FastAPI service on Cloud
Run, triaged/investigated/diagnosed by Claude agents through an explicit
state machine, with a mandatory human approval gate before any risky action
executes. Full design: `ARCHITECTURE.md`. Day-to-day log: `STATUS.md`.

## Current phase

Step 3 of the Build Order (`ARCHITECTURE.md` §20) is **done**: all four
agents plus the Validator now exist. Step 4 (production controls —
"Pydantic validation, guardrails, permissions, retries, fallbacks, human
approval" per §20) is **in progress**: human approval is done; the
retry/fallback policy work (the still-deferred retry-wrapper refactor)
is not. Failure injection and real execution of an approved action are
step 5 ("Deploy"), not step 4 — not started.

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
- Next: rest of step 4 (production controls) — retry/fallback policy
  for agent LLM calls, and the cost/budget circuit breaker mentioned in
  `agent-rules.md`, are still open. Confirm scope before beginning.

Don't jump ahead to step 5 (deploy — includes real execution of an
approved action and failure injection) or later steps until step 4 is
done.

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
