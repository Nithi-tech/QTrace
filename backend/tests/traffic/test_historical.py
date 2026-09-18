from datetime import datetime, timezone

from app.traffic.historical import day_of_week, time_bucket_minutes


def test_day_of_week_monday_is_zero():
    monday = datetime(2026, 9, 21, 8, 7, tzinfo=timezone.utc)
    assert day_of_week(monday) == 0


def test_time_bucket_floors_to_bucket_start():
    at = datetime(2026, 9, 21, 8, 7, tzinfo=timezone.utc)
    assert time_bucket_minutes(at, bucket_size_minutes=15) == 8 * 60
