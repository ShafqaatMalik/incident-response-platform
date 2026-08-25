# Testing rules

Source of truth: `ARCHITECTURE.md` §12–13.

## The pyramid

1. **Unit** — functions, validators, policies, tools, services in
   isolation. No network, no DB, no LLM calls.
2. **Integration** — real boundaries between two components: API↔database,
   API↔agents, agents↔tools, workflow↔execution. Use a real (test)
   database; still no live LLM calls.
3. **Workflow** — full incident scenarios end-to-end (incident →
   investigation → diagnosis → approval → remediation → verification).
   **LLM calls are mocked** — deterministic, fast, free. These tests
   verify the state machine and data flow, not model quality.
4. **Failure** — LLM timeout, invalid AI output, tool timeout, missing
   data, conflicting evidence, failed remediation, retry-limit exhaustion.
   Each of these must resolve to a defined, tested outcome (retry,
   fallback, or escalate) — never an unhandled exception.
5. **Evaluation** — the real ~15–20 case incident dataset run against
   **live models**. This is the only layer that costs money and calls a
   real LLM.

## Hard rule: mocked vs live

- Unit/integration/workflow/failure tests must never make a live LLM call.
  If a test needs one to pass, it's actually an evaluation test — move it.
- Only evaluation tests hit live models, and they run **nightly**, not per
  PR (see CI/CD below). Don't add a live-model call to anything gated on
  every push.

## CI/CD gating (per PR)

Lint → Unit → Integration → Workflow (mocked LLM) → Security checks →
Docker build → Deploy. All of these must be fast/free/deterministic — if a
new test can't meet that, it belongs in the nightly evaluation run instead.

## Failure tests are not optional

Every failure mode in `ARCHITECTURE.md` §7 needs a corresponding test that
asserts the system escalates or falls back visibly — never that it
silently succeeds or swallows the error.
