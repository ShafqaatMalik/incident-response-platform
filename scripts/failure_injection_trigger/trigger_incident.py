#!/usr/bin/env python3
"""Fires one POST /internal/failures/inject against the live API (a
random category), then runs the resulting incident through the full
triage -> investigate -> diagnose -> remediate -> validate pipeline,
sequentially. Run twice daily as a Cloud Run Job via Cloud Scheduler --
see scripts/failure_injection_trigger/Dockerfile.

An injection that fails (daily cap hit, budget exceeded, transient
error) or a pipeline that stops partway (a failed stage, or a legitimate
escalation) is expected, logged data -- not a script failure. Only a
missing environment variable is treated as a real deployment bug.
"""

import json
import logging
import os
import random
import sys
import urllib.error
import urllib.request

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("failure_injection_trigger")

CATEGORIES = ["dependency_timeout", "elevated_error_rate", "latency_spike"]
STAGES = ["triage", "investigate", "diagnose", "remediate", "validate"]

INJECT_TIMEOUT = 30.0
STAGE_TIMEOUT = 90.0


def _error_body(exc: urllib.error.HTTPError) -> str:
    try:
        return exc.read().decode("utf-8", errors="replace")[:200]
    except OSError:
        return "<no body>"


def build_inject_request(base_url: str, api_key: str, category: str) -> urllib.request.Request:
    url = base_url.rstrip("/") + "/internal/failures/inject"
    body = json.dumps({"category": category}).encode("utf-8")
    return urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "X-API-Key": api_key},
        method="POST",
    )


def build_stage_request(
    base_url: str, api_key: str, incident_id: str, stage: str
) -> urllib.request.Request:
    url = f"{base_url.rstrip('/')}/internal/incidents/{incident_id}/{stage}"
    return urllib.request.Request(url, data=b"", headers={"X-API-Key": api_key}, method="POST")


def inject(base_url: str, api_key: str, *, rng: random.Random | None = None) -> str | None:
    category = (rng or random).choice(CATEGORIES)
    request = build_inject_request(base_url, api_key, category)
    try:
        with urllib.request.urlopen(request, timeout=INJECT_TIMEOUT) as response:
            incident_id = json.loads(response.read())["id"]
            logger.info("injected %s -> incident %s", category, incident_id)
            return str(incident_id)
    except urllib.error.HTTPError as exc:
        logger.warning(
            "injection failed (category=%s): HTTP %s %s", category, exc.code, _error_body(exc)
        )
        return None
    except (urllib.error.URLError, TimeoutError) as exc:
        logger.warning("injection failed (category=%s): %s", category, exc)
        return None


def run_stage(base_url: str, api_key: str, incident_id: str, stage: str) -> tuple[bool, str | None]:
    request = build_stage_request(base_url, api_key, incident_id, stage)
    try:
        with urllib.request.urlopen(request, timeout=STAGE_TIMEOUT) as response:
            status = json.loads(response.read())["status"]
            logger.info("incident %s stage %s -> %s", incident_id, stage, status)
            return True, status
    except urllib.error.HTTPError as exc:
        logger.warning(
            "incident %s stage %s failed: HTTP %s %s",
            incident_id,
            stage,
            exc.code,
            _error_body(exc),
        )
        return False, None
    except (urllib.error.URLError, TimeoutError) as exc:
        logger.warning("incident %s stage %s failed: %s", incident_id, stage, exc)
        return False, None


def run_pipeline(base_url: str, api_key: str, incident_id: str) -> str:
    status = None
    for stage in STAGES:
        ok, status = run_stage(base_url, api_key, incident_id, stage)
        if not ok:
            return f"stopped at {stage} (call failed)"
        if status == "escalated":
            return f"escalated during {stage}"
    return f"completed -> {status}"


def main() -> int:
    try:
        base_url = os.environ["TARGET_BASE_URL"]
        api_key = os.environ["API_KEY"]
    except KeyError as exc:
        logger.error("missing required environment variable: %s", exc)
        return 1

    incident_id = inject(base_url, api_key)
    if incident_id is None:
        logger.info("no incident created this run (injection failed or capped) -- exiting cleanly")
        return 0

    outcome = run_pipeline(base_url, api_key, incident_id)
    logger.info("incident %s pipeline outcome: %s", incident_id, outcome)
    return 0


if __name__ == "__main__":
    sys.exit(main())
