"""add investigation fields

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "incidents", sa.Column("error_patterns", postgresql.ARRAY(sa.Text()), nullable=True)
    )
    op.add_column("incidents", sa.Column("deployment_correlation", sa.Text(), nullable=True))
    op.add_column("incidents", sa.Column("service_health_summary", sa.Text(), nullable=True))
    op.add_column(
        "incidents", sa.Column("investigation_confidence", sa.String(length=16), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("incidents", "investigation_confidence")
    op.drop_column("incidents", "service_health_summary")
    op.drop_column("incidents", "deployment_correlation")
    op.drop_column("incidents", "error_patterns")
