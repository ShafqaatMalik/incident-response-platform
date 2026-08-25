# Incident Response Platform — Claude Code Guide

AI-assisted incident response system: a monitored FastAPI service on Cloud
Run, triaged/investigated/diagnosed by Claude agents through an explicit
state machine, with a mandatory human approval gate before any risky action
executes. Full design: `ARCHITECTURE.md`. Day-to-day log: `STATUS.md`.

## Current phase

Harness setup (`ARCHITECTURE.md` §20, step 1). **No application code yet.**
Do not create `app/`, `tests/`, `evals/`, `migrations/`, or `frontend/`
until this phase is explicitly done and the user says to move on.

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
- No dev/test/deploy commands are defined yet — nothing to run until the
  FastAPI foundation exists.
