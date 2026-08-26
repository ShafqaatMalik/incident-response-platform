import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IncidentStatus(StrEnum):
    DETECTED = "detected"
    TRIAGED = "triaged"
    INVESTIGATING = "investigating"
    ESCALATED = "escalated"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Confidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=IncidentStatus.DETECTED.value
    )
    trigger: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str | None] = mapped_column(String(16), nullable=True)
    affected_service: Mapped[str | None] = mapped_column(String(255), nullable=True)
    symptoms: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    evidence: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    escalation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_patterns: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    deployment_correlation: Mapped[str | None] = mapped_column(Text, nullable=True)
    service_health_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    investigation_confidence: Mapped[str | None] = mapped_column(String(16), nullable=True)
