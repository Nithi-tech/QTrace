"""add tracking_sessions and location_pings - driver location tracking and
admin fleet monitoring (additive, does not touch any existing table)

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-18

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tracking_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tracking_code", sa.String(12), nullable=False, unique=True),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("optimization_jobs.id"), nullable=False),
        sa.Column("vehicle_index", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_tracking_sessions_tracking_code", "tracking_sessions", ["tracking_code"], unique=True)
    op.create_index("ix_tracking_sessions_job_id", "tracking_sessions", ["job_id"])

    op.create_table(
        "location_pings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("tracking_sessions.id"), nullable=False),
        sa.Column("latitude", sa.Float, nullable=False),
        sa.Column("longitude", sa.Float, nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_location_pings_session_id", "location_pings", ["session_id"])


def downgrade() -> None:
    op.drop_table("location_pings")
    op.drop_table("tracking_sessions")
