from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DailySpend(Base):
    __tablename__ = "daily_spend"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    total_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 6), nullable=False, server_default="0"
    )
