import asyncio
import logging
from functools import partial

from celery import Celery

from taskmanager.domain.events import DomainEvent, TaskAssigned, TaskCompleted
from taskmanager.infrastructure.tasks import names

logger = logging.getLogger(__name__)


class CeleryEventPublisher:
    """Turns domain events into background jobs (SPEC-005).

    Jobs are sent *by name*, so the API never imports the worker's code. Enqueueing happens on a
    worker thread so the event loop never blocks on the broker, and a broker failure is logged
    instead of failing a request whose data is already committed (R4). The wait is bounded
    (R7, CR-001): an unreachable Redis otherwise blocks for ~6 s while redis-py retries.
    """

    def __init__(self, app: Celery, *, timeout_seconds: float = 2.0) -> None:
        self._app = app
        self._timeout_seconds = timeout_seconds

    async def publish(self, event: DomainEvent) -> None:
        name, kwargs = self._job_for(event)
        try:
            await asyncio.wait_for(
                asyncio.to_thread(self._dispatch, name, kwargs),
                timeout=self._timeout_seconds,
            )
        except Exception:
            logger.exception("Could not enqueue background job for %s", type(event).__name__)

    def _dispatch(self, name: str, kwargs: dict[str, str]) -> None:
        registered = self._app.tasks.get(name)
        if registered is not None and self._app.conf.task_always_eager:
            # Eager mode (tests, local debugging): run the registered job in-process.
            registered.apply(kwargs=kwargs, throw=True)
        else:
            partial(self._app.send_task, name, kwargs=kwargs, retry=False)()

    @staticmethod
    def _job_for(event: DomainEvent) -> tuple[str, dict[str, str]]:
        """Map an event to its job. Unknown events fail loudly instead of as 'broker errors'."""
        match event:
            case TaskAssigned(task_id=task_id, assignee_id=assignee_id, assigned_by=assigned_by):
                return names.TASK_ASSIGNED, {
                    "task_id": str(task_id),
                    "assignee_id": str(assignee_id),
                    "assigned_by": str(assigned_by),
                }
            case TaskCompleted(task_id=task_id, completed_by=completed_by):
                return names.TASK_COMPLETED, {
                    "task_id": str(task_id),
                    "completed_by": str(completed_by),
                }
            case _:
                raise TypeError(f"No background job for event {type(event).__name__}")
