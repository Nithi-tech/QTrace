"""Traffic snapshot domain model - the CURRENT aggregated state of one road segment.

CLAUDE.md #7, #12: provider, timestamp, road/route info, speed/congestion.

`provider`, `road_or_route_info`, `speed_kph`, and `congestion_level` are the original
columns from this model's first version (generic, provider-labeled, not tied to a
specific segment). They predate the QTrace crowd-telemetry system and are not written
by it - kept, unused, for backward compatibility rather than dropped (CLAUDE.md #47,
#55: never edit/drop schema that might already be in use without a controlled
migration strategy). The columns below are what app/traffic/service.py actually reads
and writes.
"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, new_uuid


class TrafficSnapshot(Base):
    """Time-dependent, provider-labeled traffic data. Never presented as live unless it is (CLAUDE.md #12)."""

    __tablename__ = "traffic_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    road_or_route_info: Mapped[dict] = mapped_column(JSON, nullable=False)
    speed_kph: Mapped[float | None] = mapped_column(Float, nullable=True)
    congestion_level: Mapped[float | None] = mapped_column(Float, nullable=True)

    # --- QTrace crowd-telemetry fields (current state per segment) ---
    segment_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("traffic_segments.id"), nullable=True, index=True
    )
    current_speed_mps: Mapped[float | None] = mapped_column(Float, nullable=True)
    reference_speed_mps: Mapped[float | None] = mapped_column(Float, nullable=True)
    congestion_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-1
    observation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-1
    # LIVE / RECENT / STALE / EXPIRED / UNKNOWN - see app/traffic/aggregation.py
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="UNKNOWN")
