import os
from datetime import UTC, datetime, timedelta

import asyncpg
from cleanup_synthetic_documents import delete_old_synthetic_documents, to_asyncpg_dsn
from sqlalchemy.ext.asyncio import AsyncEngine


def test_to_asyncpg_dsn_strips_sqlalchemy_dialect_suffix() -> None:
    assert (
        to_asyncpg_dsn("postgresql+asyncpg://user:pass@host:5432/db")
        == "postgresql://user:pass@host:5432/db"
    )


def test_to_asyncpg_dsn_leaves_plain_dsn_unchanged() -> None:
    dsn = "postgresql://user:pass@host:5432/db"
    assert to_asyncpg_dsn(dsn) == dsn


async def _insert_document(
    conn: asyncpg.Connection, *, is_synthetic: bool, created_at: datetime
) -> str:
    row = await conn.fetchrow(
        """
        INSERT INTO documents
            (id, source_text, summary, word_count, sentence_count,
             readability_score, created_at, is_synthetic)
        VALUES (gen_random_uuid(), 'text', 'summary', 1, 1, 1.0, $1, $2)
        RETURNING id
        """,
        created_at,
        is_synthetic,
    )
    return str(row["id"])


async def test_delete_only_targets_documents_that_are_both_synthetic_and_expired(
    engine: AsyncEngine,
) -> None:
    conn = await asyncpg.connect(to_asyncpg_dsn(os.environ["DATABASE_URL"]))
    try:
        now = datetime.now(UTC)
        old = now - timedelta(days=4)

        old_synthetic_id = await _insert_document(conn, is_synthetic=True, created_at=old)
        recent_synthetic_id = await _insert_document(conn, is_synthetic=True, created_at=now)
        old_real_id = await _insert_document(conn, is_synthetic=False, created_at=old)
        recent_real_id = await _insert_document(conn, is_synthetic=False, created_at=now)

        cutoff = now - timedelta(days=3)
        deleted_ids = await delete_old_synthetic_documents(conn, cutoff=cutoff)

        # Only the row that is BOTH is_synthetic=true AND older than the
        # cutoff was deleted -- the other three (wrong age, wrong flag, or
        # neither) all survive.
        assert deleted_ids == [old_synthetic_id]

        remaining_ids = {str(row["id"]) for row in await conn.fetch("SELECT id FROM documents")}
        assert remaining_ids == {recent_synthetic_id, old_real_id, recent_real_id}
    finally:
        await conn.close()
