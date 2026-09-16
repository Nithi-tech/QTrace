"""Day-of-week / time-bucket helpers for the historical baseline (CLAUDE.md
traffic-free-system master-prompt #14). Pure, timezone-explicit (CLAUDE.md #40 -
callers must pass timezone-aware UTC datetimes; bucketing is done in UTC, not local
time, to keep behavior identical across regions/cities).
"""

from datetime import datetime

DEFAULT_BUCKET_SIZE_MINUTES = 15


def day_of_week(at: datetime) -> int:
    """0=Monday .. 6=Sunday (Python's own convention, used as-is rather than inventing
    a different numbering)."""
    return at.weekday()


def time_bucket_minutes(at: datetime, bucket_size_minutes: int = DEFAULT_BUCKET_SIZE_MINUTES) -> int:
    """Minute-of-day, floored to the start of its bucket - e.g. 08:07 with a 15-minute
    bucket returns 480 (08:00)."""
    minute_of_day = at.hour * 60 + at.minute
    return (minute_of_day // bucket_size_minutes) * bucket_size_minutes
