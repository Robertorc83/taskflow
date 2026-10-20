"""Celery tasks: thin adapters that decode arguments and run an application use case."""

from typing import Any
from uuid import UUID

from celery import Task
from celery.signals import task_postrun, task_prerun
from sqlalchemy.exc import OperationalError

from taskmanager.application.ports import Notifier, UnitOfWork
from taskmanager.application.use_cases.notifications import NotifyTaskAssigned, NotifyTaskCompleted
from taskmanager.infrastructure.logging import request_id_var
from taskmanager.infrastructure.tasks import names
from taskmanager.infrastructure.tasks.celery_app import celery_app
from taskmanager.infrastructure.tasks.runtime import get_runtime

# Retry policy (SPEC-005 R5): exponential backoff with jitter, at most 3 retries — and only for
# failures that can heal (database/network). A bad argument or a bug fails immediately.
TRANSIENT_ERRORS = (OperationalError, ConnectionError, TimeoutError)


@task_prerun.connect
def _adopt_request_id(task: "Task[Any, Any]", **_: Any) -> None:  # generic only in stubs
    """Log every line of a job under the ID of the request that enqueued it (CR-013)."""
    request = task.request
    # A broker delivers custom headers as request attributes; eager `apply` keeps them nested.
    request_id = getattr(request, names.REQUEST_ID_HEADER, None) or (request.headers or {}).get(
        names.REQUEST_ID_HEADER
    )
    request_id_var.set(request_id)


@task_postrun.connect
def _forget_request_id(**_: Any) -> None:
    request_id_var.set(None)  # a worker process runs many jobs; never carry one into the next


@celery_app.task(
    name=names.TASK_ASSIGNED,
    autoretry_for=TRANSIENT_ERRORS,
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
    name=names.TASK_COMPLETED,
    autoretry_for=TRANSIENT_ERRORS,
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def notify_task_completed(task_id: str, completed_by: str) -> None:
    async def job(uow: UnitOfWork, notifier: Notifier) -> None:
        await NotifyTaskCompleted(uow, notifier).execute(UUID(task_id), UUID(completed_by))

    get_runtime().run(job)
