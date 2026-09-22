"""Traffic data retention (CLAUDE.md #17, traffic master-prompt retention section).

Raw crowd-telemetry observations are kept only briefly (TRAFFIC_RAW_RETENTION_DAYS) -
they exist to feed snapshots/historical profiles, not to be queried individually
after the fact. Aggregated snapshots are kept longer (TRAFFIC_SNAPSHOT_RETENTION_DAYS).
Historical profiles are never purged here - they are a small, bounded (segment x
day-of-week x time-bucket) running aggregate, not raw data that grows unbounded.
"""

from dataclasses import dataclass
from datetime import datetime

from app.repositories.traffic_repository import TrafficRepository, retention_cutoffs


@dataclass
class RetentionResult:
    observations_deleted: int
    snapshots_deleted: int


def purge_expired_traffic_data(
    repository: TrafficRepository,
    now: datetime,
    raw_retention_days: int,
    snapshot_retention_days: int,
) -> RetentionResult:
    raw_cutoff, snapshot_cutoff = retention_cutoffs(now, raw_retention_days, snapshot_retention_days)
    observations_deleted, snapshots_deleted = repository.purge_expired(raw_cutoff, snapshot_cutoff)
    repository.commit()
    return RetentionResult(observations_deleted=observations_deleted, snapshots_deleted=snapshots_deleted)
