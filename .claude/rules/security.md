# Security & production-safety rules

Source of truth: `ARCHITECTURE.md` §6.

## Hard prohibitions

AI agents/tools must never be able to, in any environment code runs in:
- Delete data
- Expose secrets (API keys, credentials, connection strings, tokens) in
  logs, responses, or committed files
- Modify arbitrary infrastructure (no free-form `gcloud`/`terraform`/infra
  CLI access handed to an agent or tool)
- Execute dangerous/unbounded shell commands
- Make unrestricted production changes

## Human approval gate

Any high-risk action follows exactly this sequence, with no shortcut path:

AI recommendation → validation → **human approval** → execution

- "High-risk" is defined by the remediation's tool/action type, decided in
  code (the validator / a policy module), not by the LLM's own judgment of
  risk.
- Never implement a remediation action that executes before an `Approval`
  record exists and is `approved`.

## Permissions live in code, not prompts

- Enforce what an agent/tool is allowed to do via application-layer
  permission checks (allowlists, policy modules, scoped tool
  definitions) — never rely on a system prompt instruction alone to
  prevent a dangerous action.
- When adding a new tool for an agent to call, default it to the minimum
  capability needed; require an explicit, reviewed change to grant more.

## Failure injection

- Failure injection triggers are internal-only (e.g. an authenticated
  admin/internal endpoint or env-gated flag) — never reachable by a real
  visitor, and never presented in a way that could be mistaken for a real
  outage by anyone outside the project.
- Keep injection on a capped schedule (a few per day) — this is a cost
  control as much as a safety one; don't build an "always on" chaos mode.

## Secrets

- Never commit `.env`, connection strings, or API keys. Confirm anything
  read from env vars is not echoed into logs, evidence records, or LLM
  context that later gets displayed to a user.
