"""Delivery stop domain model.

CLAUDE.md #7: address/location, demand, priority, service time, time window.
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, new_uuid


class DeliveryStop(Base, TimestampMixin):
    __tablename__ = "delivery_stops"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    demand: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    service_time_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    time_window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    time_window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
