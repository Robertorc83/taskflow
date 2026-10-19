"""Idempotent demo data (SPEC-008 D2): `python -m taskmanager.seed`.

Tasks are created through the domain model "as of" a past date, so overdue examples still obey
every invariant instead of bypassing them.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from taskmanager.application.ports import PasswordHasher, UnitOfWork
from taskmanager.domain.entities import Task, User
from taskmanager.domain.value_objects import TaskStatus
from taskmanager.infrastructure.clock import SystemClock
from taskmanager.infrastructure.config import Settings, get_settings
from taskmanager.infrastructure.db.session import create_engine, create_session_factory
from taskmanager.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from taskmanager.infrastructure.security.passwords import Argon2PasswordHasher

logger = logging.getLogger(__name__)

DEMO_USERS = [
    ("alice@example.com", "Alice Smith", "Alice123!"),
    ("bob@example.com", "Bob Jones", "Bob12345!"),
    ("carol@example.com", "Carol Diaz", "Carol123!"),
]


@dataclass(frozen=True)
class DemoTask:
    title: str
    owner: str
    status: TaskStatus = TaskStatus.PENDING
    created_days_ago: int = 1
    due_in_days: int | None = None  # relative to today; negative = overdue
    assignee: str | None = None
    description: str | None = None


DEMO_TASKS = [
    DemoTask(
        "Prepare Q4 roadmap",
        "alice",
        due_in_days=10,
        assignee="bob",
        description="Collect input from every team lead and draft the roadmap.",
    ),
    DemoTask("Review onboarding docs", "alice", TaskStatus.IN_PROGRESS, 4, due_in_days=2),
    DemoTask(
        "Fix flaky login test",
        "alice",
        created_days_ago=8,
        due_in_days=-2,
        assignee="carol",
        description="Fails roughly 1 in 20 runs on CI.",
    ),
    DemoTask("Book team offsite venue", "alice", TaskStatus.COMPLETED, 12, due_in_days=-5),
    DemoTask("Write release notes", "alice", due_in_days=0),
    DemoTask("Clean up feature flags", "alice"),
    DemoTask(
        "Update dependencies", "alice", TaskStatus.IN_PROGRESS, 3, due_in_days=6, assignee="bob"
    ),
    DemoTask(
        "Interview backend candidate",
        "alice",
        TaskStatus.COMPLETED,
        6,
        due_in_days=-1,
        assignee="carol",
    ),
    DemoTask("Plan sprint 42", "alice", due_in_days=3),
    DemoTask("Archive old dashboards", "alice", created_days_ago=20, due_in_days=-9),
    DemoTask("Draft security checklist", "alice", due_in_days=21),
    DemoTask("Reply to customer feedback", "alice", TaskStatus.IN_PROGRESS, 2, due_in_days=1),
    DemoTask(
        "Set up error alerting",
        "bob",
        due_in_days=5,
        assignee="alice",
        description="Page on-call when the 5xx rate goes above 1% for 5 minutes.",
    ),
    DemoTask(
        "Benchmark list endpoint", "bob", TaskStatus.IN_PROGRESS, 5, due_in_days=4, assignee="alice"
    ),
    DemoTask("Rotate API keys", "bob", created_days_ago=10, due_in_days=-3, assignee="alice"),
    DemoTask("Refactor billing module", "bob", due_in_days=14),
    DemoTask("Migrate CI to new runners", "bob", TaskStatus.COMPLETED, 9, due_in_days=-4),
    DemoTask("Write ADR for caching", "bob"),
    DemoTask("Design empty states", "carol", due_in_days=7, assignee="alice"),
    DemoTask(
        "Accessibility audit", "carol", TaskStatus.IN_PROGRESS, 6, due_in_days=9, assignee="bob"
    ),
    DemoTask("Update brand colors", "carol", TaskStatus.COMPLETED, 15, due_in_days=-7),
    DemoTask("User interviews round 2", "carol", due_in_days=12),
    DemoTask(
        "Prototype mobile filters", "carol", created_days_ago=7, due_in_days=-1, assignee="bob"
    ),
    DemoTask("Icon set refresh", "carol"),
    DemoTask("Usability test report", "carol", due_in_days=2, assignee="alice"),
]


def _build_task(spec: DemoTask, users: dict[str, User], now: datetime) -> Task:
    created_at = now - timedelta(days=spec.created_days_ago)
    due_date = (
        now.date() + timedelta(days=spec.due_in_days) if spec.due_in_days is not None else None
    )
    owner = users[spec.owner]
    task = Task.create(
        title=spec.title,
        description=spec.description,
        due_date=due_date,
        owner_id=owner.id,
        now=created_at,
    )
    if spec.assignee:
        task.assign_to(users[spec.assignee].id, assigned_by=owner.id, now=created_at)
    if spec.status is TaskStatus.IN_PROGRESS:
        task.change_status(TaskStatus.IN_PROGRESS, now=created_at + timedelta(hours=2))
    elif spec.status is TaskStatus.COMPLETED:
        completed_by = users[spec.assignee].id if spec.assignee else owner.id
        task.complete(completed_by=completed_by, now=created_at + timedelta(days=1))
    task.pull_events()  # demo data must not trigger notifications
    return task


async def seed(uow: UnitOfWork, hasher: PasswordHasher, now: datetime) -> bool:
    """Insert demo users and tasks. Returns False (and changes nothing) if already seeded."""
    async with uow:
        if await uow.users.get_by_email(DEMO_USERS[0][0]):
            return False
        users: dict[str, User] = {}
        for email, full_name, password in DEMO_USERS:
            user = User.register(
                email=email,
                full_name=full_name,
                hashed_password=hasher.hash(password),
                now=now - timedelta(days=30),
            )
            await uow.users.add(user)
            users[email.split("@", maxsplit=1)[0]] = user
        for spec in DEMO_TASKS:
            await uow.tasks.add(_build_task(spec, users, now))
        await uow.commit()
    return True


def should_seed(settings: Settings) -> bool:
    """Demo accounts have published passwords: never create them in production (CR-002)."""
    return settings.seed_demo_data and settings.environment != "production"


async def _main() -> None:
    settings = get_settings()
    if not should_seed(settings):
        logger.info("Demo data disabled (SEED_DEMO_DATA=false or production) — skipped")
        return
    engine = create_engine(settings.database_url, pooled=False)
    try:
        uow = SqlAlchemyUnitOfWork(create_session_factory(engine))
        seeded = await seed(uow, Argon2PasswordHasher(), SystemClock().now())
    finally:
        await engine.dispose()
    logger.info("Demo data %s", "created" if seeded else "already present — skipped")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_main())


if __name__ == "__main__":
    main()
