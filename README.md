# Incident Response Platform

A small, deployed production service, monitored by a multi-agent
system that investigates real failures, proposes safe remediation, and
requires human approval before acting on anything risky.


## What this is

A FastAPI service runs continuously on Google Cloud Run and takes real and
deliberately-injected traffic and failures. When something breaks, a
sequence of AI agents investigates it end to end:

```
Live API → Logs/Metrics → Incident Detected
  → Triage → Investigation → Diagnosis → Remediation Proposal
  → Validation → Human Approval → Execution → Verification
  → Resolved / Escalated
```

Nothing risky ever executes without an explicit human approval step. The
system is designed to fail safely and visibly — timeouts, invalid AI
output, and low-confidence diagnoses all route to a human rather than
guessing or silently failing.

## Why this exists

This is a project demonstrating that AI agents can be integrated
into a safe, observable, testable, production-grade software workflow —
not a demo of "AI agents talking to each other."

## Stack

- **API:** FastAPI + Pydantic
- **Agents:** Claude Agent SDK
- **Database:** Supabase (Postgres)
- **Deployment:** Docker + Google Cloud Run
- **CI/CD:** GitHub Actions
- **Observability:** OpenTelemetry → Google Cloud Logging/Trace
- **Frontend:** React + TypeScript dashboard

## Local development

_(to be filled in once the FastAPI foundation is in place)_
