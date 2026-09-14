# Incident Response Platform

## What this is

A production-oriented incident response system, live on Google Cloud Run
today. A FastAPI service runs continuously and takes real and
deliberately-injected failures; each incident runs through four
Claude-driven agents — Triage, Investigation, Diagnosis, Remediation — plus
a non-AI Validator, ending at a mandatory human approval gate. Three
automated background jobs generate genuine incidents around the clock, an
18-scenario evaluation harness grades the agents nightly against live
models, and a React dashboard, hosted on Netlify, lets a reviewer inspect
and act on every incident in real time.

## Why this exists

This project demonstrates that AI agents can be integrated into a system
trustworthy enough for real infrastructure — not staged, not mocked, and
not agents talking to each other for its own sake. Four things back that
up:

- **Safe, structured integration.** Every agent call returns a
  Pydantic-validated output, never a raw string consumed downstream. The
  incident lifecycle is a fixed state machine, not free-form agent chat —
  no transition happens without an explicit, logged step, and nothing
  risky ever executes without a human decision.
- **Cost-aware operation.** A budget circuit breaker halts new AI calls
  once daily spend hits $2.00. Per-incident cost is tracked to the
  fraction of a cent — $0.034 on average across the evaluation set, not
  estimated after the fact.
- **Evaluated, not just deployed.** An 18-scenario dataset runs against
  live models nightly, graded by both deterministic rule checks and an
  LLM judge, on a two-phase trust model where every judge verdict carries
  its own reasoning for review before it's trusted unattended.
- **Real, not staged.** Failure injection creates genuine incidents
  through the same code path as any real one. Two background jobs
  trigger the full pipeline automatically, around the clock, generating
  ongoing evidence of how the system behaves.

The point isn't a system that looks impressive in a five-minute
walkthrough. It's a system built the way software touching real
infrastructure has to be built.

## Architecture

- **[Incident lifecycle](docs/architecture-pipeline.md)** — how an
  incident moves through the four agents, the Validator, and the human
  approval gate.
- **[Live infrastructure](docs/architecture-infra.md)** — the deployed
  Cloud Run/Supabase/Netlify topology, including the three background
  jobs and their schedules.

## What's actually live

- **Dashboard:** [irp-dashboard.netlify.app](https://irp-dashboard.netlify.app)
  — view incidents, inspect every stage's evidence, approve or reject.
- **Backend:** a real FastAPI service on Google Cloud Run, backed by a
  real Supabase Postgres database — not a local or in-memory stand-in.
- **Three automated background jobs**, each a Cloud Run Job on its own
  Cloud Scheduler trigger:
  - `irp-synthetic-traffic` — every 7 minutes, posts realistic traffic
    to keep the service genuinely active.
  - `irp-synthetic-cleanup` — daily at 03:17 UTC, deletes synthetic
    documents older than 3 days.
  - `irp-failure-injection-trigger` — daily at 06:43 and 18:43 UTC,
    creates one real incident and runs it through the full pipeline
    automatically.
- **Evaluation, run nightly against live models:** 18 real-world
  incident scenarios, 94.4% escalation correctness, 100% on
  valid-action-type, evidence-present, and validator-not-bypassed rates,
  $0.034 mean cost per incident.
- **Failure injection**, available on demand or via the automated
  trigger above: 5 categories — `dependency_timeout`,
  `elevated_error_rate`, `latency_spike`, `gradual_degradation`,
  `isolated_incident` — capped at 5 per day.
- **Two spending limits enforced automatically, not just documented:** a
  $2.00/day AI budget cap and a 5/day failure-injection cap, both backed
  by real database counters, both returning a `429` the moment they're
  hit.

## Tech stack

- **API:** FastAPI + Pydantic
- **Agents:** plain Anthropic Python SDK (`client.messages.parse()`) —
  one structured-output call per agent, no tool-use loop, no agent
  framework
- **Database:** Supabase (Postgres)
- **Deployment:** Docker + Google Cloud Run (one service, three
  background Jobs) + Cloud Scheduler
- **CI/CD:** GitHub Actions
- **Observability:** OpenTelemetry → Google Cloud Trace, Prometheus
  metrics
- **Frontend:** React + TypeScript, hosted on Netlify

## How I found and fixed real bugs

The evaluation harness's job is to catch exactly this kind of failure —
and it did. Early runs showed nearly every Investigation stage telling
the same story, regardless of what actually triggered the incident: a
fabricated "v1.42.0 deployment reduced the connection pool" narrative,
whether or not a deployment was involved at all.

The root cause was in the tool layer, not the agent: `get_recent_logs`,
`get_deployment_history`, and `get_service_metrics` returned fixed,
hardcoded content no matter what evidence the incident actually
described. The fix replaced all three with one shared `select_scenario()`
function, so the tools agree with each other and with the real trigger
text by construction, instead of drifting independently.

The result is measured, not assumed: hallucinations flagged by the LLM
judge dropped from 10 of 18 scenarios to 2 of 18, across two real
evaluation runs using the same judge model — a direct, before-and-after
result from the harness doing its job.

## Safety design

- **A fixed six-action list**, each with a risk level decided in code,
  never by the model: `restart_service` (medium), `rollback_deployment`
  (high), `scale_up` (low), `disable_traffic` (high), `no_action_needed`
  (low), `manual_investigation_required` (none).
- **A rule-based Validator** sits between the Remediation agent's
  proposal and human approval — a fixed set of code checks
  (evidence-supported, permitted, structurally valid), not another model
  call.
- **A mandatory human approval gate.** Every incident that reaches a
  proposed action stops at `AWAITING_APPROVAL` until a person explicitly
  approves or rejects it, with a required reason for rejection. Real
  execution of an approved action was never built — the system's
  terminal states are `APPROVED`, `REJECTED`, or `ESCALATED`, nothing
  further.
- **A budget circuit breaker.** Daily AI spend is tracked per call; once
  it crosses $2.00, new agent calls are blocked until the next day.
