"""Pipeline job management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from evograph.db.models import PipelineRun
from evograph.db.session import get_db

router = APIRouter(tags=["jobs"])


class JobSubmitRequest(BaseModel):
    step: str
    scope: str = "Aves"
    strategy: str = "api"
    resume: bool = False
    skip_existing: bool = True
    k: int = 15


class JobResponse(BaseModel):
    id: str
    step: str
    scope: str
    status: str
    celery_task_id: str | None = None
    error: str | None = None
    started_at: str | None = None
    finished_at: str | None = None


class JobListResponse(BaseModel):
    jobs: list[JobResponse]
    total: int


VALID_STEPS = {
    "ingest_ott",
    "ingest_ncbi",
    "select_canonical",
    "build_neighbors",
    "build_kmer_index",
    "validate",
}


@router.post("/jobs/pipeline", response_model=JobResponse)
def submit_pipeline_job(req: JobSubmitRequest, db: Session = Depends(get_db)) -> JobResponse:
    """Submit a pipeline step for background execution."""
    if req.step not in VALID_STEPS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid step '{req.step}'. Valid steps: {sorted(VALID_STEPS)}",
        )

    # Import task functions
    from evograph.tasks import pipeline_tasks as tasks

    task_map = {
        "ingest_ott": lambda: tasks.task_ingest_ott.delay(
            scope=req.scope, strategy=req.strategy, resume=req.resume
        ),
        "ingest_ncbi": lambda: tasks.task_ingest_ncbi.delay(
            skip_existing=req.skip_existing
        ),
        "select_canonical": lambda: tasks.task_select_canonical.delay(),
        "build_neighbors": lambda: tasks.task_build_neighbors.delay(
            strategy=req.strategy, k=req.k
        ),
        "build_kmer_index": lambda: tasks.task_build_kmer_index.delay(),
        "validate": lambda: tasks.task_validate.delay(),
    }

    result = task_map[req.step]()

    # The task itself creates the PipelineRun record, but we need to wait briefly
    # or return the celery task ID for polling
    return JobResponse(
        id="",  # Will be set by the task
        step=req.step,
        scope=req.scope,
        status="submitted",
        celery_task_id=result.id,
    )


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)) -> JobResponse:
    """Get status of a pipeline job."""
    run = db.query(PipelineRun).filter(PipelineRun.id == job_id).first()
    if run is None:
        # Try finding by celery task ID
        run = db.query(PipelineRun).filter(PipelineRun.celery_task_id == job_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobResponse(
        id=run.id,
        step=run.step,
        scope=run.scope,
        status=run.status,
        celery_task_id=run.celery_task_id,
        error=run.error,
        started_at=run.started_at.isoformat() if run.started_at else None,
        finished_at=run.finished_at.isoformat() if run.finished_at else None,
    )


@router.get("/jobs", response_model=JobListResponse)
def list_jobs(
    step: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> JobListResponse:
    """List pipeline jobs with optional filtering."""
    query = db.query(PipelineRun)
    if step:
        query = query.filter(PipelineRun.step == step)
    if status:
        query = query.filter(PipelineRun.status == status)

    total = query.count()
    runs = query.order_by(PipelineRun.created_at.desc()).limit(limit).all()

    return JobListResponse(
        jobs=[
            JobResponse(
                id=r.id,
                step=r.step,
                scope=r.scope,
                status=r.status,
                celery_task_id=r.celery_task_id,
                error=r.error,
                started_at=r.started_at.isoformat() if r.started_at else None,
                finished_at=r.finished_at.isoformat() if r.finished_at else None,
            )
            for r in runs
        ],
        total=total,
    )
