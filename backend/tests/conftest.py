"""Shared fixtures.

The database is a real PostgreSQL, started once per session with testcontainers (or taken from
TEST_DATABASE_URL, e.g. a CI service container) and migrated with Alembic — so the migrations
themselves are under test. Each test that needs it starts from empty tables.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from pydantic import SecretStr
from sqlalchemy import create_engine, text

from taskmanager.infrastructure.config import Settings

pytest_plugins = [
    "tests.step_defs.world",
    "tests.step_defs.common_steps",
    "tests.step_defs.auth_steps",
    "tests.step_defs.task_steps",
    "tests.step_defs.listing_steps",
    "tests.step_defs.notification_steps",
    "tests.step_defs.rate_limit_steps",
]

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _sync_url(async_url: str) -> str:
    return async_url.replace("+asyncpg", "+psycopg2")


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    if url := os.environ.get("TEST_DATABASE_URL"):
        yield url
        return

    from testcontainers.community.postgres import PostgresContainer  # noqa: PLC0415 — only when needed

    with PostgresContainer("postgres:16-alpine", driver="asyncpg") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture(scope="session")
def migrated_database(database_url: str) -> str:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    config.attributes["configure_logger"] = False
    command.upgrade(config, "head")
    return database_url


@pytest.fixture
def clean_database(migrated_database: str) -> None:
    engine = create_engine(_sync_url(migrated_database))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE tasks, users CASCADE"))
    engine.dispose()


@pytest.fixture
def test_settings(migrated_database: str) -> Settings:
    return Settings(
        environment="test",
        database_url=migrated_database,
        jwt_secret=SecretStr("test-secret-that-is-long-enough-for-hs256"),
        rate_limit_enabled=False,
        rate_limit_storage_uri="memory://",
        celery_task_always_eager=True,
    )
