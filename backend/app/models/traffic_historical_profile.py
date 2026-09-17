"""Learned historical baseline: this segment's typical speed at this day-of-week and
time-of-day, aggregated from QTrace's own past observations (CLAUDE.md traffic-free-
system master-prompt #14). Long retention - this is the whole point of collecting it.

median_speed_mps here is a running-mean approximation, not a true rolling median (an
exact rolling median would require keeping every raw sample indefinitely, which
TRAFFIC_RAW_RETENTION_DAYS explicitly prevents) - documented in
app/traffic/service.py::_update_historical_profile.
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, new_uuid


class TrafficHistoricalProfile(Base):
    __tablename__ = "traffic_historical_profiles"
    __table_args__ = (
        UniqueConstraint(
            "segment_id", "day_of_week", "time_bucket_minutes", name="uq_traffic_historical_profile_bucket"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    segment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("traffic_segments.id"), nullable=False, index=True
    )
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=Monday .. 6=Sunday
    time_bucket_minutes: Mapped[int] = mapped_column(Integer, nullable=False)  # bucket start, minute-of-day
    median_speed_mps: Mapped[float] = mapped_column(Float, nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
