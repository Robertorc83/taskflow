import asyncio
import logging
from typing import Any

from celery import Celery

from taskmanager.domain.events import DomainEvent, TaskAssigned, TaskCompleted
from taskmanager.infrastructure.tasks.jobs import notify_task_assigned, notify_task_completed

logger = logging.getLogger(__name__)


class CeleryEventPublisher:
    """Turns domain events into background jobs (SPEC-005).

    Enqueueing happens on a worker thread so the event loop never blocks on the broker, and a
    broker failure is logged instead of failing a request whose data is already committed (R4).
    The wait is bounded (R7, CR-001): an unreachable Redis otherwise blocks for ~6 s while
    redis-py retries the connection.
    """

    def __init__(self, app: Celery, *, timeout_seconds: float = 2.0) -> None:
        self._app = app
        self._timeout_seconds = timeout_seconds

    async def publish(self, event: DomainEvent) -> None:
        match event:
            case TaskAssigned(task_id=task_id, assignee_id=assignee_id, assigned_by=assigned_by):
                job: Any = notify_task_assigned
                kwargs = {
                    "task_id": str(task_id),
                    "assignee_id": str(assignee_id),
                    "assigned_by": str(assigned_by),
                }
            case TaskCompleted(task_id=task_id, completed_by=completed_by):
                job = notify_task_completed
                kwargs = {"task_id": str(task_id), "completed_by": str(completed_by)}
        try:
            await asyncio.wait_for(
                asyncio.to_thread(job.apply_async, kwargs=kwargs, retry=False),
                timeout=self._timeout_seconds,
            )
        except Exception:
            logger.exception("Could not enqueue background job for %s", type(event).__name__)
