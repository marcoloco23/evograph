"""Celery task wrappers for pipeline steps.

Each task wraps an existing pipeline function, adds progress tracking via
the pipeline_runs table, and reports results back through Celery.
"""

from __future__ import annotations

import asyncio
import logging
import traceback
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import insert as pg_insert

from evograph.db.models import PipelineRun
from evograph.db.session import SessionLocal
from evograph.worker import celery_app

logger = logging.getLogger(__name__)


def _update_run(run_id: str, **kwargs) -> None:
    """Update a pipeline_runs record."""
    session = SessionLocal()
    try:
        from sqlalchemy import update
        stmt = update(PipelineRun).where(PipelineRun.id == run_id).values(**kwargs)
        session.execute(stmt)
        session.commit()
    finally:
        session.close()


def _run_pipeline_step(run_id: str, step: str, func, *args, **kwargs) -> dict:
    """Execute a pipeline step with tracking."""
    _update_run(run_id, status="running", started_at=datetime.now(timezone.utc))

    try:
        # If the function is async, run it in an event loop
        if asyncio.iscoroutinefunction(func):
            asyncio.run(func(*args, **kwargs))
        else:
            func(*args, **kwargs)

        _update_run(
            run_id,
            status="completed",
            finished_at=datetime.now(timezone.utc),
        )
        return {"status": "completed", "step": step, "run_id": run_id}

    except Exception:
        _update_run(
            run_id,
            status="failed",
            finished_at=datetime.now(timezone.utc),
            error=traceback.format_exc(),
        )
        raise


def _create_run(step: str, scope: str, celery_task_id: str) -> str:
    """Create a pipeline_runs record and return its ID."""
    import uuid
    run_id = str(uuid.uuid4())
    session = SessionLocal()
    try:
        stmt = pg_insert(PipelineRun).values(
            id=run_id,
            step=step,
            scope=scope,
            status="pending",
            celery_task_id=celery_task_id,
        )
        session.execute(stmt)
        session.commit()
    finally:
        session.close()
    return run_id


@celery_app.task(bind=True, name="pipeline.ingest_ott")
def task_ingest_ott(self, scope: str = "Aves", strategy: str = "api", resume: bool = False):
    """Ingest OpenTree taxonomy."""
    from evograph.pipeline.ingest_ott import ingest
    run_id = _create_run("ingest_ott", scope, self.request.id)
    return _run_pipeline_step(run_id, "ingest_ott", ingest, scope=scope, strategy=strategy, resume=resume)


@celery_app.task(bind=True, name="pipeline.ingest_ncbi")
def task_ingest_ncbi(self, limit: int | None = None, skip_existing: bool = True):
    """Ingest NCBI COI sequences."""
    from evograph.pipeline.ingest_ncbi import ingest
    run_id = _create_run("ingest_ncbi", "all", self.request.id)
    return _run_pipeline_step(run_id, "ingest_ncbi", ingest, limit=limit, skip_existing=skip_existing)


@celery_app.task(bind=True, name="pipeline.select_canonical")
def task_select_canonical(self):
    """Select canonical sequences."""
    from evograph.pipeline.select_canonical import select_canonical
    run_id = _create_run("select_canonical", "all", self.request.id)
    return _run_pipeline_step(run_id, "select_canonical", select_canonical)


@celery_app.task(bind=True, name="pipeline.build_neighbors")
def task_build_neighbors(self, strategy: str = "family", k: int = 15):
    """Build kNN neighbor edges."""
    from evograph.pipeline.build_neighbors import build_neighbors
    run_id = _create_run("build_neighbors", "all", self.request.id)
    return _run_pipeline_step(run_id, "build_neighbors", build_neighbors, strategy=strategy, k=k)


@celery_app.task(bind=True, name="pipeline.build_kmer_index")
def task_build_kmer_index(self):
    """Build FAISS k-mer index."""
    from evograph.pipeline.build_kmer_index import build
    run_id = _create_run("build_kmer_index", "all", self.request.id)
    return _run_pipeline_step(run_id, "build_kmer_index", build)


@celery_app.task(bind=True, name="pipeline.validate")
def task_validate(self):
    """Run validation pipeline."""
    from evograph.pipeline.validate import validate
    run_id = _create_run("validate", "all", self.request.id)
    return _run_pipeline_step(run_id, "validate", validate)
