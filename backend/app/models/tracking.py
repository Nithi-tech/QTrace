"""Vehicle tracking domain models - driver location reporting and admin fleet
monitoring. Entirely additive: does not change OptimizationJob or any other
existing table.

A TrackingSession links one vehicle's planned route (an entry in
OptimizationJob.result["vehicle_routes"]) to a short `tracking_code` a driver
enters in the app. Route data itself (stops, geometry) is not duplicated here
- it is read from the job's already-stored result JSON by (job_id,
vehicle_index) - a TrackingSession only needs to hold that reference plus the
code. LocationPing rows are the periodic GPS updates the driver's app reports
while en route, which is what both the driver's own map and the admin's
fleet-wide view are built from (app/services/tracking_service.py).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, new_uuid


class TrackingSession(Base, TimestampMixin):
    __tablename__ = "tracking_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tracking_code: Mapped[str] = mapped_column(String(12), nullable=False, unique=True, index=True)
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("optimization_jobs.id"), nullable=False, index=True
    )
    vehicle_index: Mapped[int] = mapped_column(Integer, nullable=False)

    pings: Mapped[list["LocationPing"]] = relationship(
        back_populates="session", order_by="LocationPing.recorded_at", cascade="all, delete-orphan"
    )


class LocationPing(Base):
    __tablename__ = "location_pings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tracking_sessions.id"), nullable=False, index=True
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    # Server-stamped on receipt (not client-supplied) so distance/off-route
    # calculations aren't at the mercy of a driver device's clock being wrong.
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    session: Mapped[TrackingSession] = relationship(back_populates="pings")
