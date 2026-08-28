"""add approval fields

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-28

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("incidents", sa.Column("approved_by", sa.String(length=255), nullable=True))
    op.add_column("incidents", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("incidents", sa.Column("rejected_by", sa.String(length=255), nullable=True))
    op.add_column("incidents", sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("incidents", sa.Column("rejection_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("incidents", "rejection_reason")
    op.drop_column("incidents", "rejected_at")
    op.drop_column("incidents", "rejected_by")
    op.drop_column("incidents", "approved_at")
    op.drop_column("incidents", "approved_by")
