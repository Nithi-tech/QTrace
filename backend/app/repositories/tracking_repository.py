from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.optimization_job import OptimizationJob
from app.models.tracking import LocationPing, TrackingSession


class TrackingRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create_session(self, job_id: str, vehicle_index: int, tracking_code: str) -> TrackingSession:
        session = TrackingSession(job_id=job_id, vehicle_index=vehicle_index, tracking_code=tracking_code)
        self._db.add(session)
        self._db.commit()
        self._db.refresh(session)
        return session

    def code_exists(self, tracking_code: str) -> bool:
        return self._db.query(TrackingSession).filter_by(tracking_code=tracking_code).first() is not None

    def get_by_code(self, tracking_code: str) -> TrackingSession | None:
        return self._db.query(TrackingSession).filter_by(tracking_code=tracking_code).first()

    def get_job(self, job_id: str) -> OptimizationJob | None:
        return self._db.get(OptimizationJob, job_id)

    def list_sessions_for_job(self, job_id: str) -> list[TrackingSession]:
        return self._db.query(TrackingSession).filter_by(job_id=job_id).order_by(TrackingSession.vehicle_index).all()

    def add_ping(self, session_id: str, latitude: float, longitude: float) -> LocationPing:
        ping = LocationPing(
            session_id=session_id,
            latitude=latitude,
            longitude=longitude,
            recorded_at=datetime.now(timezone.utc),
        )
        self._db.add(ping)
        self._db.commit()
        self._db.refresh(ping)
        return ping

    def list_pings(self, session_id: str) -> list[LocationPing]:
        return (
            self._db.query(LocationPing)
            .filter_by(session_id=session_id)
            .order_by(LocationPing.recorded_at)
            .all()
        )
