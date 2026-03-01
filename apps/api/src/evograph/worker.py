"""Celery application factory for background pipeline tasks."""

from celery import Celery

from evograph.settings import settings

celery_app = Celery(
    "evograph",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    result_expires=86400,  # 24 hours
    worker_prefetch_multiplier=1,  # One task at a time (pipeline tasks are heavy)
    task_acks_late=True,  # Acknowledge after completion for reliability
)

# Auto-discover tasks from the tasks module
celery_app.autodiscover_tasks(["evograph.tasks"])
