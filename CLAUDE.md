# Incident Response Platform — Claude Code Guide

AI-assisted incident response system: a monitored FastAPI service on Cloud
Run, triaged/investigated/diagnosed by Claude agents through an explicit
state machine, with a mandatory human approval gate before any risky action
executes. Full design: `ARCHITECTURE.md`. Day-to-day log: `STATUS.md`.

## Current phase

Step 3 of the Build Order (`ARCHITECTURE.md` §20): **add the agents.**

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
- Next: Diagnosis and Remediation agents, then the Validator.

Don't jump ahead to step 4 (production controls), step 5 (deploy), or
later steps until all four agents and the Validator exist.

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
