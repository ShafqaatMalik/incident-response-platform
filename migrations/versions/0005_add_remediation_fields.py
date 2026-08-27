"""add remediation fields

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-27

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "incidents", sa.Column("proposed_action_type", sa.String(length=64), nullable=True)
    )
    op.add_column("incidents", sa.Column("action_risk_level", sa.String(length=16), nullable=True))
    op.add_column("incidents", sa.Column("action_justification", sa.Text(), nullable=True))
    op.add_column("incidents", sa.Column("action_detail", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("incidents", "action_detail")
    op.drop_column("incidents", "action_justification")
    op.drop_column("incidents", "action_risk_level")
    op.drop_column("incidents", "proposed_action_type")
