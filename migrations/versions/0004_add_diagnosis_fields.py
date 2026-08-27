"""add diagnosis fields

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-27

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("incidents", sa.Column("root_cause", sa.Text(), nullable=True))
    op.add_column(
        "incidents",
        sa.Column("alternative_explanations", postgresql.ARRAY(sa.Text()), nullable=True),
    )
    op.add_column(
        "incidents", sa.Column("diagnosis_confidence", sa.String(length=16), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("incidents", "diagnosis_confidence")
    op.drop_column("incidents", "alternative_explanations")
    op.drop_column("incidents", "root_cause")
