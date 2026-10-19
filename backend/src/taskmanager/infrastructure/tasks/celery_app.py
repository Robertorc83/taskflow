from typing import Any

from celery import Celery

from taskmanager.infrastructure.config import Settings


def _conf(settings: Settings) -> dict[str, Any]:
    return {
        "broker_url": settings.broker_url,
        "task_always_eager": settings.celery_task_always_eager,
        "task_serializer": "json",
        "accept_content": ["json"],
        "task_acks_late": True,
        "task_reject_on_worker_lost": True,
        "worker_prefetch_multiplier": 1,
        "broker_connection_retry_on_startup": True,
        "task_ignore_result": True,
    }


def create_celery_app(settings: Settings) -> Celery:
    """A producer-only app for the API: enqueues jobs by name, never imports the worker."""
    app = Celery("taskmanager-api")
    app.conf.update(_conf(settings))
    return app


# The worker's app; its jobs register on it (see jobs.py) and worker.py configures it.
celery_app = Celery("taskmanager", include=["taskmanager.infrastructure.tasks.jobs"])


def configure_celery(settings: Settings) -> Celery:
    celery_app.conf.update(_conf(settings))
    return celery_app
