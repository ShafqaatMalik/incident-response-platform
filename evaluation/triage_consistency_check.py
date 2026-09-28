#!/usr/bin/env python3
"""One-time diagnostic: calls the Triage Agent directly, N times per
failure-injection category, using the exact fixed trigger text
app/policies/failure_injection_policy.py already defines, and prints
the severity distribution per category. Triage only -- no
investigate/diagnose/remediate/judge calls -- to check whether the
severity rubric actually produces consistent results for the same
input, cheaper and faster than a full evaluation harness run.

No live HTTP calls, no daily_failure_injection_limit consumed, no
incidents table touched -- but it does make real Triage Agent calls
against live models and records real spend via record_spend(), same
as any other live Triage call, so it still counts against the
$2.00/day budget cap.

Run explicitly: `uv run python evaluation/triage_consistency_check.py`
"""

import asyncio
import sys
from collections import Counter
from urllib.parse import urlparse

from app.agents.triage import call_triage_agent_with_retry
from app.core.config import get_settings
from app.db.session import get_sessionmaker
from app.models.schemas import TriageContext
from app.policies.failure_injection_policy import FailureCategory, build_injection_trigger

RUNS_PER_CATEGORY = 5

_LOCAL_HOSTS = {"localhost", "127.0.0.1"}


def _ensure_local_database(database_url: str) -> None:
    """Refuses to run unless DATABASE_URL points at localhost.

    This script records real spend via record_spend() on every Triage
    call, same as any other live call -- it must never be able to write
    those rows against a live/production database, regardless of what
    DATABASE_URL happens to be set to when someone runs this.
    """
    normalized = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    host = urlparse(normalized).hostname
    if host not in _LOCAL_HOSTS:
        print(
            f"Refusing to run: DATABASE_URL points at '{host}', not localhost. "
            "This script writes real spend rows and must never run against a "
            "live/production database.",
            file=sys.stderr,
        )
        raise SystemExit(1)


async def main() -> int:
    settings = get_settings()
    _ensure_local_database(settings.database_url)

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        for category in FailureCategory:
            trigger, evidence = build_injection_trigger(category)
            context = TriageContext(trigger=trigger, initial_evidence=evidence)
            counts: Counter[str] = Counter()
            for _ in range(RUNS_PER_CATEGORY):
                result = await call_triage_agent_with_retry(context, settings.triage_model, session)
                counts[result.severity] += 1
            print(f"{category.value}: {dict(counts)}")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
