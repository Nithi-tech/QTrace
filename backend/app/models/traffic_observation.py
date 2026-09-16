"""A single anonymized speed observation on one road segment, derived from QTrace's own
GPS telemetry map-matched against OSRM (CLAUDE.md #7). Short retention by design -
see app/traffic/retention.py and TRAFFIC_RAW_RETENTION_DAYS.

No user/device identity is stored here (CLAUDE.md traffic-free-system master-prompt #7,
#9, #42) - only what is needed to compute a segment's current speed.
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, new_uuid


class TrafficObservation(Base):
    __tablename__ = "traffic_observations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    segment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("traffic_segments.id"), nullable=False, index=True
    )
    # The real, observed speed for this segment - distance from OSRM's map-matching,
    # elapsed time from the phone's own GPS timestamps (app/routing/map_matching.py).
    # Never fabricated (CLAUDE.md traffic-free-system master-prompt #25).
    observed_speed_mps: Mapped[float] = mapped_column(Float, nullable=False)
    accuracy_m: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
