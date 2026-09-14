#!/usr/bin/env python3
"""One-time diagnostic: fires BURST_COUNT failure-injection requests at
the live incident-response-platform API in genuine parallel, then runs
each resulting incident through the full triage -> investigate ->
diagnose -> remediate -> validate pipeline, also in parallel across
incidents, to observe how the live system behaves under concurrent
load.

This is a manual, one-off run (not a scheduled job) -- invoke with:

    export TARGET_BASE_URL=https://incident-response-platform-hkpzk7dxzq-ts.a.run.app
    export API_KEY=...
    uv run python scripts/burst_test/burst_test.py

Before running: raise DAILY_FAILURE_INJECTION_LIMIT on the live Cloud
Run service (the default cap of 5 is below BURST_COUNT's default of
10). After running: revert it. Both are gcloud commands you run
yourself -- this script never touches live infra config, only the API.
See scripts/burst_test/README.md for the exact commands.
"""

import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("burst_test")

CATEGORIES = ["dependency_timeout", "elevated_error_rate", "latency_spike"]
STAGES = ["triage", "investigate", "diagnose", "remediate", "validate"]

# Pipeline stage calls trigger real LLM calls and can run slower under
# concurrent load -- generous timeout so a slow-but-healthy response
# isn't misreported as a client-side timeout failure.
REQUEST_TIMEOUT = httpx.Timeout(120.0, connect=10.0)


@dataclass
class InjectionResult:
    index: int
    category: str
    success: bool
    incident_id: str | None
    error: str | None
    latency_seconds: float


@dataclass
class StageResult:
    stage: str
    success: bool
    status: str | None
    error: str | None
    latency_seconds: float


@dataclass
class IncidentPipelineResult:
    incident_id: str
    stages: list[StageResult] = field(default_factory=list)

    @property
    def final_status(self) -> str | None:
        for stage in reversed(self.stages):
            if stage.status is not None:
                return stage.status
        return None


def _parse_error(response: httpx.Response) -> str:
    try:
        body = response.json()
        detail = body.get("error", {})
        code = detail.get("code", "unknown")
        message = detail.get("message", response.text[:200])
        return f"{response.status_code} {code}: {message}"
    except (json.JSONDecodeError, AttributeError):
        return f"{response.status_code}: {response.text[:200]}"


async def inject_one(client: httpx.AsyncClient, index: int) -> InjectionResult:
    category = CATEGORIES[index % len(CATEGORIES)]
    start = time.monotonic()
    try:
        response = await client.post("/internal/failures/inject", json={"category": category})
    except httpx.HTTPError as exc:
        elapsed = time.monotonic() - start
        logger.warning("injection %d (%s) failed: %s", index, category, exc)
        error = f"{type(exc).__name__}: {exc}"
        return InjectionResult(index, category, False, None, error, elapsed)

    elapsed = time.monotonic() - start
    if response.status_code == 201:
        incident_id = response.json()["id"]
        logger.info(
            "injection %d (%s) -> incident %s (%.2fs)", index, category, incident_id, elapsed
        )
        return InjectionResult(index, category, True, incident_id, None, elapsed)

    error = _parse_error(response)
    logger.warning("injection %d (%s) failed: %s", index, category, error)
    return InjectionResult(index, category, False, None, error, elapsed)


async def run_injections(client: httpx.AsyncClient, count: int) -> list[InjectionResult]:
    return list(await asyncio.gather(*(inject_one(client, i) for i in range(count))))


async def run_stage(client: httpx.AsyncClient, incident_id: str, stage: str) -> StageResult:
    start = time.monotonic()
    try:
        response = await client.post(f"/internal/incidents/{incident_id}/{stage}")
    except httpx.HTTPError as exc:
        elapsed = time.monotonic() - start
        logger.warning("incident %s stage %s failed: %s", incident_id, stage, exc)
        return StageResult(stage, False, None, f"{type(exc).__name__}: {exc}", elapsed)

    elapsed = time.monotonic() - start
    if response.status_code == 200:
        status = response.json()["status"]
        logger.info("incident %s stage %s -> %s (%.2fs)", incident_id, stage, status, elapsed)
        return StageResult(stage, True, status, None, elapsed)

    error = _parse_error(response)
    logger.warning("incident %s stage %s failed: %s", incident_id, stage, error)
    return StageResult(stage, False, None, error, elapsed)


async def run_pipeline_for_incident(
    client: httpx.AsyncClient, incident_id: str
) -> IncidentPipelineResult:
    result = IncidentPipelineResult(incident_id=incident_id)
    for stage in STAGES:
        stage_result = await run_stage(client, incident_id, stage)
        result.stages.append(stage_result)
        if not stage_result.success:
            break
        if stage_result.status == "escalated":
            break
    return result


async def run_pipelines(
    client: httpx.AsyncClient, incident_ids: list[str]
) -> list[IncidentPipelineResult]:
    return list(
        await asyncio.gather(*(run_pipeline_for_incident(client, iid) for iid in incident_ids))
    )


def _summarize(
    injections: list[InjectionResult],
    pipelines: list[IncidentPipelineResult],
    injection_seconds: float,
    pipeline_seconds: float,
) -> str:
    lines = ["", "=" * 70, "BURST TEST SUMMARY", "=" * 70]

    injected_ok = [r for r in injections if r.success]
    injected_fail = [r for r in injections if not r.success]
    lines.append(
        f"\nPhase 1 -- injection: {len(injected_ok)}/{len(injections)} succeeded "
        f"in {injection_seconds:.2f}s (wall clock, {len(injections)} concurrent requests)"
    )
    for r in injected_fail:
        lines.append(f"  FAILED  index={r.index} category={r.category}: {r.error}")

    lines.append(
        f"\nPhase 2 -- pipelines: {len(pipelines)} incident(s) run "
        f"in {pipeline_seconds:.2f}s (wall clock, concurrent across incidents)"
    )
    status_counts: dict[str, int] = {}
    error_counts: dict[str, int] = {}
    for p in pipelines:
        final = p.final_status or "no_stage_succeeded"
        status_counts[final] = status_counts.get(final, 0) + 1
        failed_stage = next((s for s in p.stages if not s.success), None)
        if failed_stage:
            key = failed_stage.error or "unknown_error"
            error_counts[key] = error_counts.get(key, 0) + 1

    lines.append("  Final status distribution:")
    for status, count in sorted(status_counts.items()):
        lines.append(f"    {status}: {count}")

    if error_counts:
        lines.append("  Stage failures encountered:")
        for error, count in sorted(error_counts.items()):
            lines.append(f"    x{count}  {error}")

    lines.append(f"\nTotal wall-clock time: {injection_seconds + pipeline_seconds:.2f}s")
    lines.append("=" * 70)
    return "\n".join(lines)


async def run(base_url: str, api_key: str, burst_count: int, report_path: Path) -> int:
    started_at = datetime.now(UTC)
    async with httpx.AsyncClient(
        base_url=base_url,
        headers={"X-API-Key": api_key, "Content-Type": "application/json"},
        timeout=REQUEST_TIMEOUT,
    ) as client:
        injection_start = time.monotonic()
        injections = await run_injections(client, burst_count)
        injection_seconds = time.monotonic() - injection_start

        incident_ids = [r.incident_id for r in injections if r.success and r.incident_id]
        pipeline_start = time.monotonic()
        pipelines = await run_pipelines(client, incident_ids) if incident_ids else []
        pipeline_seconds = time.monotonic() - pipeline_start

    finished_at = datetime.now(UTC)
    print(_summarize(injections, pipelines, injection_seconds, pipeline_seconds))

    report = {
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "target_base_url": base_url,
        "burst_count": burst_count,
        "injection_phase": {
            "duration_seconds": injection_seconds,
            "results": [asdict(r) for r in injections],
        },
        "pipeline_phase": {
            "duration_seconds": pipeline_seconds,
            "results": [
                {
                    "incident_id": p.incident_id,
                    "final_status": p.final_status,
                    "stages": [asdict(s) for s in p.stages],
                }
                for p in pipelines
            ],
        },
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\nFull report written to {report_path}")
    print(
        "\nREMINDER: revert the live failure-injection cap now -- "
        "see scripts/burst_test/README.md for the exact gcloud command."
    )
    return 0


def main() -> int:
    try:
        base_url = os.environ["TARGET_BASE_URL"]
        api_key = os.environ["API_KEY"]
    except KeyError as exc:
        logger.error("missing required environment variable: %s", exc)
        return 1

    burst_count = int(os.environ.get("BURST_COUNT", "10"))
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    report_path = Path(__file__).parent / "reports" / f"{timestamp}.json"

    return asyncio.run(run(base_url, api_key, burst_count, report_path))


if __name__ == "__main__":
    sys.exit(main())
