"""Optimization job domain model (CLAUDE.md #7, #25 - queued/running/completed/failed/cancelled)."""

import enum
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, new_uuid


class OptimizationJobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class OptimizationJob(Base, TimestampMixin):
    __tablename__ = "optimization_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    input_dataset: Mapped[dict] = mapped_column(JSON, nullable=False)
    objective: Mapped[dict] = mapped_column(JSON, nullable=False)
    algorithm: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[OptimizationJobStatus] = mapped_column(
        Enum(OptimizationJobStatus), default=OptimizationJobStatus.QUEUED, nullable=False, index=True
    )
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
