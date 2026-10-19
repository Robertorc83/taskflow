"""Celery tasks: thin adapters that decode arguments and run an application use case."""

from uuid import UUID

from taskmanager.application.ports import Notifier, UnitOfWork
from taskmanager.application.use_cases.notifications import NotifyTaskAssigned, NotifyTaskCompleted
from taskmanager.infrastructure.tasks.celery_app import celery_app
from taskmanager.infrastructure.tasks.runtime import get_runtime

# Retry policy (SPEC-005 R5): exponential backoff with jitter, at most 3 retries.


@celery_app.task(
    name="notifications.task_assigned",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def notify_task_assigned(task_id: str, assignee_id: str, assigned_by: str) -> None:
    async def job(uow: UnitOfWork, notifier: Notifier) -> None:
        await NotifyTaskAssigned(uow, notifier).execute(
            UUID(task_id), UUID(assignee_id), UUID(assigned_by)
        )

    get_runtime().run(job)


@celery_app.task(
    name="notifications.task_completed",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def notify_task_completed(task_id: str, completed_by: str) -> None:
    async def job(uow: UnitOfWork, notifier: Notifier) -> None:
        await NotifyTaskCompleted(uow, notifier).execute(UUID(task_id), UUID(completed_by))

    get_runtime().run(job)
