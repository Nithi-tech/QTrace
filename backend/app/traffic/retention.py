"""Retention purge (CLAUDE.md traffic-free-system master-prompt #27) - short-lived raw
observations, longer-lived aggregated snapshots. Deliberately a plain callable rather
than a scheduled RQ job: app/workers/ has no job-queue wiring yet in this codebase
(CLAUDE.md #46 - don't build unneeded infrastructure), so this is invoked directly via
`python -m app.traffic.retention` from a cron entry until that infrastructure exists.
"""

import logging
from datetime import datetime, timezone

from app.repositories.traffic_repository import TrafficRepository, retention_cutoffs

logger = logging.getLogger(__name__)


def purge_expired_traffic_data(
    repository: TrafficRepository, now: datetime, raw_retention_days: int, snapshot_retention_days: int
) -> tuple[int, int]:
    raw_cutoff, snapshot_cutoff = retention_cutoffs(now, raw_retention_days, snapshot_retention_days)
    observations_deleted, snapshots_deleted = repository.purge_expired(raw_cutoff, snapshot_cutoff)
    logger.info(
        "traffic retention purge: %d observations, %d snapshots deleted (raw_cutoff=%s, snapshot_cutoff=%s)",
        observations_deleted,
        snapshots_deleted,
        raw_cutoff,
        snapshot_cutoff,
    )
    return observations_deleted, snapshots_deleted


if __name__ == "__main__":
    from app.core.config import get_settings
    from app.core.db import SessionLocal

    settings = get_settings()
    db = SessionLocal()
    try:
        purge_expired_traffic_data(
            TrafficRepository(db),
            now=datetime.now(timezone.utc),
            raw_retention_days=settings.traffic_raw_retention_days,
            snapshot_retention_days=settings.traffic_snapshot_retention_days,
        )
        db.commit()
    finally:
        db.close()
