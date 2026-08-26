"""create incidents table

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("trigger", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=True),
        sa.Column("affected_service", sa.String(length=255), nullable=True),
        sa.Column("symptoms", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("evidence", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("escalation_reason", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("incidents")
