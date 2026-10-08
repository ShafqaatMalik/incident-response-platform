#!/usr/bin/env python3
"""One-off: bulk-reject stale awaiting_approval incidents on the live backend.

Talks only to the existing API (GET /internal/incidents, paginated, and
POST /internal/incidents/{id}/reject) -- no direct database access. It has
no code path that can approve: the only POST it can send is a reject, and
the HTTP client refuses any other POST path.

Default is a dry run. Nothing is rejected unless --yes is passed.

    uv run python scripts/bulk_reject_incidents.py --base-url https://<service>.run.app
    uv run python scripts/bulk_reject_incidents.py --base-url ... --before 2026-10-01 --yes

Selection: of all incidents whose status is exactly "awaiting_approval",
the newest --keep-latest N (default 3) are always left alone; --before
then further limits the rest to incidents created strictly before that
date/time (UTC if no offset is given).

The API key is read from Secret Manager at run time and held only in
memory -- never printed, logged, or written to disk.
"""

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Protocol

AWAITING_APPROVAL = "awaiting_approval"
REJECTED_BY = "bulk-cleanup"
REJECTION_REASON = "Synthetic test incident, bulk cleanup"
PAGE_SIZE = 100  # the list endpoint's maximum `limit`
REQUEST_TIMEOUT = 30.0

_REJECT_PATH = re.compile(r"/internal/incidents/[0-9a-fA-F-]{36}/reject")


class ApiClient(Protocol):
    def get_json(self, path: str) -> dict[str, Any]: ...

    def post_json(self, path: str, body: dict[str, Any]) -> dict[str, Any]: ...


class UrllibApiClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    def _send(self, request: urllib.request.Request) -> dict[str, Any]:
        request.add_header("X-API-Key", self._api_key)
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            result: dict[str, Any] = json.loads(response.read())
            return result

    def get_json(self, path: str) -> dict[str, Any]:
        return self._send(urllib.request.Request(self._base_url + path, method="GET"))

    def post_json(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        # Code-level guard, not just convention: this script may only ever
        # POST a reject. Anything else (e.g. /approve) is refused outright.
        if not _REJECT_PATH.fullmatch(path):
            raise ValueError(f"refusing POST to non-reject path: {path}")
        request = urllib.request.Request(
            self._base_url + path,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        return self._send(request)


def read_api_key() -> str:
    """Fetches the key from Secret Manager. Only gcloud's exit code and
    stderr are ever shown on failure -- never stdout, which holds the key."""
    result = subprocess.run(
        ["gcloud", "secrets", "versions", "access", "latest", "--secret=api-key"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"gcloud secrets access failed (exit {result.returncode}): {result.stderr.strip()}"
        )
    key = result.stdout.strip()
    if not key:
        raise RuntimeError("gcloud returned an empty api-key secret")
    return key


def fetch_all_incidents(client: ApiClient) -> tuple[list[dict[str, Any]], int]:
    """Walks every page of GET /internal/incidents (newest first). Returns
    the unique incidents seen plus the server's reported total. Incidents
    created mid-walk shift offsets, so results are de-duplicated by id."""
    seen: dict[str, dict[str, Any]] = {}
    offset = 0
    total = 0
    while True:
        page = client.get_json(f"/internal/incidents?limit={PAGE_SIZE}&offset={offset}")
        items: list[dict[str, Any]] = page["items"]
        total = int(page["total"])
        for item in items:
            seen.setdefault(str(item["id"]), item)
        offset += len(items)
        if not items or offset >= total:
            break
    return list(seen.values()), total


def _created_at(incident: dict[str, Any]) -> datetime:
    return datetime.fromisoformat(str(incident["created_at"]))


def parse_before(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def select_targets(
    incidents: list[dict[str, Any]], keep_latest: int, before: datetime | None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Returns (to_reject, kept). Only status == "awaiting_approval" exactly
    is ever eligible; the newest `keep_latest` of those are always kept."""
    awaiting = sorted(
        (i for i in incidents if i.get("status") == AWAITING_APPROVAL),
        key=_created_at,
        reverse=True,
    )
    kept = awaiting[:keep_latest]
    candidates = awaiting[keep_latest:]
    if before is not None:
        candidates = [i for i in candidates if _created_at(i) < before]
    return candidates, kept


def _describe(incident: dict[str, Any]) -> str:
    trigger = " ".join(str(incident.get("trigger", "")).split())[:60]
    severity = incident.get("severity") or "-"
    return f"  {incident['id']}  {severity:<8}  {incident['created_at']}  {trigger}"


def run(
    client: ApiClient,
    *,
    keep_latest: int,
    before: datetime | None,
    yes: bool,
    delay: float,
    sleep: Callable[[float], None] = time.sleep,
    out: Callable[[str], None] = print,
) -> int:
    incidents, total = fetch_all_incidents(client)
    out(f"Incidents seen: {len(incidents)} (server-reported total: {total})")
    if len(incidents) != total:
        out("WARNING: seen count != total (incidents changed while paging).")
        if yes:
            out("Aborting without rejecting anything -- re-run to get a consistent view.")
            return 1

    targets, kept = select_targets(incidents, keep_latest, before)
    awaiting_count = sum(1 for i in incidents if i.get("status") == AWAITING_APPROVAL)
    out(f"awaiting_approval: {awaiting_count}, kept as newest {keep_latest}: {len(kept)}")
    for incident in kept:
        out(_describe(incident))

    mode = "Will reject" if yes else "DRY RUN -- would reject"
    out(f"{mode}: {len(targets)}")
    for incident in targets:
        out(_describe(incident))

    if not yes:
        out("Dry run only. Re-run with --yes to reject.")
        return 0

    rejected = 0
    for index, incident in enumerate(targets):
        if index:
            sleep(delay)
        try:
            response = client.post_json(
                f"/internal/incidents/{incident['id']}/reject",
                {"rejected_by": REJECTED_BY, "rejection_reason": REJECTION_REASON},
            )
        except (urllib.error.URLError, OSError, ValueError) as exc:
            out(f"ERROR rejecting {incident['id']}: {exc} -- stopping.")
            out(f"Summary: rejected {rejected} of {len(targets)}.")
            return 1
        rejected += 1
        out(f"rejected {incident['id']} -> {response.get('status')}")

    out(f"Summary: rejected {rejected} of {len(targets)}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-url", required=True, help="live backend base URL")
    parser.add_argument("--keep-latest", type=int, default=3, metavar="N")
    parser.add_argument("--before", type=parse_before, metavar="DATE")
    parser.add_argument("--delay", type=float, default=1.5, help="seconds between rejects")
    parser.add_argument("--yes", action="store_true", help="actually reject (default: dry run)")
    args = parser.parse_args(argv)
    if args.keep_latest < 0:
        parser.error("--keep-latest must be >= 0")

    try:
        client = UrllibApiClient(args.base_url, read_api_key())
        return run(
            client,
            keep_latest=args.keep_latest,
            before=args.before,
            yes=args.yes,
            delay=args.delay,
        )
    except (RuntimeError, urllib.error.URLError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
