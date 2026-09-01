"""create daily_spend table

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-01

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "daily_spend",
        sa.Column("date", sa.Date(), primary_key=True),
        sa.Column("total_cost_usd", sa.Numeric(10, 6), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("daily_spend")
