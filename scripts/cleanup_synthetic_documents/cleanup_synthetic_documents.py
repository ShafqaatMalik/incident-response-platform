#!/usr/bin/env python3
"""Deletes synthetic documents (is_synthetic = true) older than a
configurable cutoff (default 3 days). Run daily as a Cloud Run Job via
Cloud Scheduler -- see scripts/cleanup_synthetic_documents/Dockerfile.
"""

import asyncio
import logging
import os
import sys
from datetime import UTC, datetime, timedelta

import asyncpg

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("cleanup_synthetic_documents")

# is_synthetic = TRUE is a fixed literal in this query text, never a bound
# parameter or an f-string substitution -- nothing this script reads from
# its environment (DATABASE_URL, CUTOFF_DAYS) can change or bypass it.
# Only the cutoff timestamp is a bound parameter ($1).
_DELETE_QUERY = "DELETE FROM documents WHERE is_synthetic = TRUE AND created_at < $1 RETURNING id"


def to_asyncpg_dsn(database_url: str) -> str:
    """asyncpg.connect() rejects the SQLAlchemy '+asyncpg' dialect suffix
    the DATABASE_URL secret is formatted with."""
    return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


async def delete_old_synthetic_documents(
    conn: asyncpg.Connection, *, cutoff: datetime
) -> list[str]:
    rows = await conn.fetch(_DELETE_QUERY, cutoff)
    return [str(row["id"]) for row in rows]


async def run(database_url: str, cutoff_days: int) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=cutoff_days)
    conn = await asyncpg.connect(to_asyncpg_dsn(database_url), statement_cache_size=0)
    try:
        deleted_ids = await delete_old_synthetic_documents(conn, cutoff=cutoff)
    finally:
        await conn.close()

    logger.info(
        "deleted %d synthetic document(s) older than %d day(s): %s",
        len(deleted_ids),
        cutoff_days,
        deleted_ids,
    )
    return 0


def main() -> int:
    try:
        database_url = os.environ["DATABASE_URL"]
    except KeyError as exc:
        logger.error("missing required environment variable: %s", exc)
        return 1

    cutoff_days = int(os.environ.get("CUTOFF_DAYS", "3"))

    try:
        return asyncio.run(run(database_url, cutoff_days))
    except (OSError, asyncpg.PostgresError) as exc:
        # Unlike the traffic script's failed HTTP ping (soft, expected
        # occasionally), a maintenance job that can't reach the database
        # has done nothing -- this must surface as a visible failed Job
        # execution, not exit 0.
        logger.error("database connection/query failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
