"""Integration tests against the real, migrated PostgreSQL."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import Connection, text
from sqlalchemy.ext.asyncio import AsyncEngine

from taskmanager.application.dto import PageRequest, TaskFilters
from taskmanager.application.exceptions import ConflictError
from taskmanager.domain.entities import User
from taskmanager.domain.value_objects import TaskStatus
from taskmanager.infrastructure.db.models import Base
from taskmanager.infrastructure.db.session import create_engine, create_session_factory
from taskmanager.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from taskmanager.seed import DEMO_TASKS, DEMO_USERS, seed
from tests.fakes import PlainTextPasswordHasher

pytestmark = pytest.mark.integration

NOW = datetime(2026, 10, 19, 9, 0, tzinfo=UTC)


@pytest.fixture
async def engine(migrated_database: str, clean_database: None) -> AsyncIterator[AsyncEngine]:
    engine = create_engine(migrated_database, pooled=False)
    yield engine
    await engine.dispose()


def uow_for(engine: AsyncEngine) -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork(create_session_factory(engine))


async def test_migrations_match_the_models(engine: AsyncEngine) -> None:
    def diff(connection: Connection) -> list[object]:
        return list(compare_metadata(MigrationContext.configure(connection), Base.metadata))

    async with engine.connect() as connection:
        assert await connection.run_sync(diff) == []


async def test_seed_is_idempotent_and_produces_demo_data(engine: AsyncEngine) -> None:
    hasher = PlainTextPasswordHasher()

    assert await seed(uow_for(engine), hasher, NOW) is True
    assert await seed(uow_for(engine), hasher, NOW) is False

    async with uow_for(engine) as uow:
        alice = await uow.users.get_by_email("alice@example.com")
        assert alice is not None
        assert hasher.verify("Alice123!", alice.hashed_password)
        users = await uow.users.list(PageRequest(size=100))
        visible = await uow.tasks.list_visible_to(alice.id, TaskFilters(), PageRequest(size=100))
    assert users.total == len(DEMO_USERS)
    assert visible.total > 15
    statuses = {task.status for task in visible.items}
    assert statuses == set(TaskStatus)
    assert any(task.is_overdue(today=NOW.date()) for task in visible.items)
    assert len(DEMO_TASKS) >= 25


async def test_database_enforces_completed_at_consistency(engine: AsyncEngine) -> None:
    async with uow_for(engine) as uow:
        owner = User.register(email="a@example.com", full_name="A", hashed_password="x", now=NOW)
        await uow.users.add(owner)
        await uow.commit()

    async with engine.connect() as connection:
        with pytest.raises(Exception, match="completed_at_matches_status"):
            await connection.execute(
                text(
                    "INSERT INTO tasks (id, title, status, owner_id, created_at, updated_at) "
                    "VALUES (gen_random_uuid(), 't', 'completed', :owner, now(), now())"
                ),
                {"owner": owner.id},
            )


async def test_duplicate_email_race_is_reported_as_conflict(engine: AsyncEngine) -> None:
    def user() -> User:
        return User.register(email="dup@example.com", full_name="D", hashed_password="x", now=NOW)

    async with uow_for(engine) as uow:
        await uow.users.add(user())
        await uow.commit()

    with pytest.raises(ConflictError):
        async with uow_for(engine) as uow:
            await uow.users.add(user())
            await uow.commit()
