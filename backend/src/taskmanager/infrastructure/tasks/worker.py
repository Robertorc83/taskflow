"""Celery entry point: `celery -A taskmanager.infrastructure.tasks.worker worker`."""

import logging

from taskmanager.infrastructure.config import get_settings
from taskmanager.infrastructure.tasks import jobs  # noqa: F401 — registers the tasks
from taskmanager.infrastructure.tasks.celery_app import celery_app, configure_celery

settings = get_settings()
configure_celery(settings)
logging.basicConfig(level=settings.log_level)

__all__ = ["celery_app"]
