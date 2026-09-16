from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.optimization_job import OptimizationJob, OptimizationJobStatus


class OptimizationJobRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create_completed(
        self, input_dataset: dict, objective: dict, algorithm: str, result: dict
    ) -> OptimizationJob:
        now = datetime.now(timezone.utc)
        job = OptimizationJob(
            input_dataset=input_dataset,
            objective=objective,
            algorithm=algorithm,
            status=OptimizationJobStatus.COMPLETED,
            result=result,
            started_at=now,
            completed_at=now,
        )
        self._db.add(job)
        self._db.commit()
        self._db.refresh(job)
        return job

    def get_by_id(self, job_id: str) -> OptimizationJob | None:
        return self._db.get(OptimizationJob, job_id)
