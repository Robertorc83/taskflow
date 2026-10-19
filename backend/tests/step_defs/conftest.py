"""Acceptance-test wiring: the scenario world, app settings and every step definition.

pytest-bdd registers each step as a fixture in the module that defines it; importing them here
makes them visible to all scenarios in this package (and only here).
"""

import pytest
from pydantic import SecretStr

from taskmanager.infrastructure.config import Settings
from tests.step_defs.auth_steps import *  # noqa: F403
from tests.step_defs.common_steps import *  # noqa: F403
from tests.step_defs.listing_steps import *  # noqa: F403
from tests.step_defs.notification_steps import *  # noqa: F403
from tests.step_defs.rate_limit_steps import *  # noqa: F403
from tests.step_defs.task_steps import *  # noqa: F403
from tests.step_defs.world import *  # noqa: F403


@pytest.fixture
def test_settings(migrated_database: str) -> Settings:
    return Settings(
        environment="test",
        database_url=migrated_database,
        jwt_secret=SecretStr("test-secret-that-is-long-enough-for-hs256"),
        rate_limit_enabled=False,
        rate_limit_storage_uri="memory://",
        celery_task_always_eager=True,
        # Never a real broker: even a non-eager publish stays in-process.
        celery_broker_url="memory://",
    )
