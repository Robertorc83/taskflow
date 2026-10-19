"""Database fixtures shared by acceptance and integration tests.

Unit tests never request these, and nothing here imports the application at module level, so
`pytest tests/unit` loads no framework or infrastructure code.

The database is a real PostgreSQL, started once per session with testcontainers (or taken from
TEST_DATABASE_URL, e.g. a CI service container) and migrated with Alembic — so the migrations
themselves are under test. Each test that needs it starts from empty tables.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

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
    from alembic import command  # noqa: PLC0415
    from alembic.config import Config  # noqa: PLC0415

    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    config.attributes["configure_logger"] = False
    command.upgrade(config, "head")
    return database_url


@pytest.fixture
def clean_database(migrated_database: str) -> None:
    from sqlalchemy import create_engine, text  # noqa: PLC0415

    engine = create_engine(_sync_url(migrated_database))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE tasks, users CASCADE"))
    engine.dispose()
