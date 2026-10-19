"""The worker's composition root: what a background job needs to run a use case."""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from taskmanager.application.ports import Notifier, UnitOfWork
from taskmanager.infrastructure.config import Settings, get_settings
from taskmanager.infrastructure.db.session import create_engine, create_session_factory
from taskmanager.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from taskmanager.infrastructure.notifier import LoggingNotifier


@dataclass
class WorkerRuntime:
    settings: Settings
    notifier: Notifier = field(default_factory=LoggingNotifier)

    def run(self, job: Callable[[UnitOfWork, Notifier], Awaitable[None]]) -> None:
        """Run an async job on a fresh event loop with its own (unpooled) database engine."""
        asyncio.run(self._run(job))

    async def _run(self, job: Callable[[UnitOfWork, Notifier], Awaitable[None]]) -> None:
        engine = create_engine(self.settings.database_url, pooled=False)
        try:
            await job(SqlAlchemyUnitOfWork(create_session_factory(engine)), self.notifier)
        finally:
            await engine.dispose()


_runtime: WorkerRuntime | None = None


def configure_worker(runtime: WorkerRuntime | None) -> None:
    global _runtime  # noqa: PLW0603 — Celery tasks are module-level; this is their DI seam
    _runtime = runtime


def get_runtime() -> WorkerRuntime:
    global _runtime  # noqa: PLW0603
    if _runtime is None:
        _runtime = WorkerRuntime(settings=get_settings())
    return _runtime
