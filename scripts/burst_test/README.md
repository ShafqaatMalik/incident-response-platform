# Burst test (one-time diagnostic)

Fires 10 `POST /internal/failures/inject` requests at the **live**
Cloud Run service in genuine parallel, then runs each resulting
incident through the full `triage -> investigate -> diagnose ->
remediate -> validate` pipeline, also in parallel across incidents.
Purpose: observe how the live system actually behaves under
concurrent load. One-off script, not a scheduled job — safe to delete
after use.

## 1. Raise the injection cap on live (you run this, not Claude)

The default `daily_failure_injection_limit` is 5; this test needs 10+.
This is a live service-config change, so it's always user-run:

```
gcloud run services update incident-response-platform \
  --region=australia-southeast1 \
  --update-env-vars=DAILY_FAILURE_INJECTION_LIMIT=15
```

(15, not 10, in case any injections already happened earlier today —
they count against the same daily counter.)

## 2. Run the script against live

```
export TARGET_BASE_URL=https://incident-response-platform-hkpzk7dxzq-ts.a.run.app
export API_KEY=<the real live API key>
uv run python scripts/burst_test/burst_test.py
```

Optional: `BURST_COUNT` (default `10`).

The script prints a summary (per-phase success/failure counts, final
status distribution, error breakdown, timing) and writes the full
detail to `scripts/burst_test/reports/<timestamp>.json` (gitignored).

Cost note: 10 incidents through triage/investigate/diagnose/remediate
is real spend against the live `daily_budget_limit_usd` ($2.00/day),
shared with any other live traffic that day — some incidents may
legitimately hit `429 budget_exceeded` partway through if the day's
budget is already partly spent. That's expected, valid data to
observe, not a bug to work around; the script logs it clearly either
way.

## 3. Revert the injection cap immediately after

```
gcloud run services update incident-response-platform \
  --region=australia-southeast1 \
  --update-env-vars=DAILY_FAILURE_INJECTION_LIMIT=5
```

The script prints a reminder to do this at the end of its run.
