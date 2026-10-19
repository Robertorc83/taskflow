from celery import Celery

from taskmanager.infrastructure.config import Settings, get_settings

celery_app = Celery("taskmanager", include=["taskmanager.infrastructure.tasks.jobs"])


def configure_celery(settings: Settings) -> Celery:
    celery_app.conf.update(
        broker_url=settings.broker_url,
        task_always_eager=settings.celery_task_always_eager,
        task_serializer="json",
        accept_content=["json"],
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
        broker_connection_retry_on_startup=True,
        task_ignore_result=True,
    )
    return celery_app


configure_celery(get_settings())
