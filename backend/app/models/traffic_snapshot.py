"""Traffic snapshot domain model (CLAUDE.md #7, #12 - provider, timestamp, road/route info, speed/congestion)."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, new_uuid


class TrafficSnapshot(Base):
    """Time-dependent, provider-labeled traffic data (CLAUDE.md #12 - never presented as live unless it is)."""

    __tablename__ = "traffic_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    road_or_route_info: Mapped[dict] = mapped_column(JSON, nullable=False)
    speed_kph: Mapped[float | None] = mapped_column(Float, nullable=True)
    congestion_level: Mapped[float | None] = mapped_column(Float, nullable=True)
