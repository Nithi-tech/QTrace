from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_optimization_job_repository, get_optimization_service
from app.repositories.optimization_job_repository import OptimizationJobRepository
from app.schemas.optimization import OptimizationJobResponse
from app.schemas.routing import RouteRequest
from app.services.optimization_service import OptimizationService

router = APIRouter(prefix="/optimization/jobs", tags=["optimization"])


@router.post("", response_model=OptimizationJobResponse)
async def create_optimization_job(
    request: RouteRequest,
    optimization_service: OptimizationService = Depends(get_optimization_service),
) -> OptimizationJobResponse:
    job, result = await optimization_service.plan_route(request)
    return OptimizationJobResponse(
        id=job.id, status=job.status, algorithm=job.algorithm, result=result, created_at=job.created_at
    )


@router.get("/{job_id}", response_model=OptimizationJobResponse)
async def get_optimization_job(
    job_id: str,
    job_repository: OptimizationJobRepository = Depends(get_optimization_job_repository),
) -> OptimizationJobResponse:
    job = job_repository.get_by_id(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Optimization job not found")
    return OptimizationJobResponse(
        id=job.id, status=job.status, algorithm=job.algorithm, result=job.result, created_at=job.created_at
    )
