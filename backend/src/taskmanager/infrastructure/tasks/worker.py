"""Celery entry point: `celery -A taskmanager.infrastructure.tasks.worker worker`."""

from taskmanager.infrastructure.config import get_settings
from taskmanager.infrastructure.logging import configure_logging
from taskmanager.infrastructure.tasks import jobs  # noqa: F401 — registers the tasks
from taskmanager.infrastructure.tasks.celery_app import celery_app, configure_celery

settings = get_settings()
configure_celery(settings)
celery_app.conf.worker_hijack_root_logger = False  # keep our structured handler
configure_logging(settings.log_level, settings.log_format)

__all__ = ["celery_app"]
