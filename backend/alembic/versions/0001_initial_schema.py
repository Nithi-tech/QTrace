"""initial schema - users, vehicles, depots, delivery_stops, routes, route_stops,
optimization_jobs, traffic_snapshots (CLAUDE.md #7 domain model)

Revision ID: 0001
Revises:
Create Date: 2026-09-16

NOTE: written by hand, not via `alembic revision --autogenerate`, because no
PostgreSQL instance is available in this environment to generate/verify
against. It has not been executed or tested against a real database -
run `alembic upgrade head` against a real Postgres instance before relying
on it (CLAUDE.md #77/#78: do not claim validation that did not happen).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("preferences", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "vehicles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("fleet_id", sa.String(36), nullable=False),
        sa.Column("capacity", sa.Float, nullable=False),
        sa.Column("current_latitude", sa.Float, nullable=True),
        sa.Column("current_longitude", sa.Float, nullable=True),
        sa.Column("operating_constraints", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_vehicles_fleet_id", "vehicles", ["fleet_id"])

    op.create_table(
        "depots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("latitude", sa.Float, nullable=False),
        sa.Column("longitude", sa.Float, nullable=False),
        sa.Column("operating_constraints", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "delivery_stops",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("latitude", sa.Float, nullable=False),
        sa.Column("longitude", sa.Float, nullable=False),
        sa.Column("demand", sa.Float, nullable=False, server_default="0"),
        sa.Column("priority", sa.Integer, nullable=False, server_default="0"),
        sa.Column("service_time_seconds", sa.Integer, nullable=False, server_default="0"),
        sa.Column("time_window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("time_window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "routes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("vehicle_id", sa.String(36), sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("geometry", sa.JSON, nullable=True),
        sa.Column("distance_meters", sa.Float, nullable=False),
        sa.Column("duration_seconds", sa.Float, nullable=False),
        sa.Column("cost", sa.Float, nullable=True),
        sa.Column("optimization_metadata", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "route_stops",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("route_id", sa.String(36), sa.ForeignKey("routes.id"), nullable=False),
        sa.Column("delivery_stop_id", sa.String(36), sa.ForeignKey("delivery_stops.id"), nullable=False),
        sa.Column("sequence", sa.Integer, nullable=False),
    )

    op.create_table(
        "optimization_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("input_dataset", sa.JSON, nullable=False),
        sa.Column("objective", sa.JSON, nullable=False),
        sa.Column("algorithm", sa.String(50), nullable=False),
        sa.Column(
            "status",
            sa.Enum("QUEUED", "RUNNING", "COMPLETED", "FAILED", "CANCELLED", name="optimizationjobstatus"),
            nullable=False,
            server_default="QUEUED",
        ),
        sa.Column("result", sa.JSON, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_optimization_jobs_status", "optimization_jobs", ["status"])

    op.create_table(
        "traffic_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("road_or_route_info", sa.JSON, nullable=False),
        sa.Column("speed_kph", sa.Float, nullable=True),
        sa.Column("congestion_level", sa.Float, nullable=True),
    )
    op.create_index("ix_traffic_snapshots_captured_at", "traffic_snapshots", ["captured_at"])


def downgrade() -> None:
    op.drop_table("traffic_snapshots")
    op.drop_table("optimization_jobs")
    op.drop_table("route_stops")
    op.drop_table("routes")
    op.drop_table("delivery_stops")
    op.drop_table("depots")
    op.drop_table("vehicles")
    op.drop_table("users")
