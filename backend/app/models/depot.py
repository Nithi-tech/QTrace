"""Depot domain model (CLAUDE.md #7 - id, location, operating constraints)."""

from sqlalchemy import JSON, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, new_uuid


class Depot(Base, TimestampMixin):
    __tablename__ = "depots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    operating_constraints: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
