"""Fail-closed configuration (CR-002, CR-012) and publisher dispatch (CR-007)."""

import pytest
from pydantic import SecretStr, ValidationError

from taskmanager.infrastructure.config import Settings
from taskmanager.seed import should_seed


@pytest.mark.parametrize("secret", [None, "too-short"])
def test_production_refuses_a_default_or_weak_jwt_secret(secret: str | None) -> None:
    overrides = {"jwt_secret": SecretStr(secret)} if secret else {}
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(environment="production", **overrides)  # type: ignore[arg-type]


def test_production_accepts_a_strong_secret() -> None:
    Settings(environment="production", jwt_secret=SecretStr("x" * 32))


@pytest.mark.parametrize(
    ("environment", "flag", "expected"),
    [("development", True, True), ("development", False, False), ("production", True, False)],
)
def test_demo_data_is_only_seeded_when_enabled_outside_production(
    environment: str, flag: bool, expected: bool
) -> None:
    settings = Settings(
        environment=environment,
        jwt_secret=SecretStr("x" * 32),
        seed_demo_data=flag,
    )
    assert should_seed(settings) is expected


async def test_publisher_rejects_unknown_events_loudly() -> None:
    from taskmanager.infrastructure.tasks.celery_app import celery_app  # noqa: PLC0415
    from taskmanager.infrastructure.tasks.publisher import CeleryEventPublisher  # noqa: PLC0415

    with pytest.raises(TypeError, match="No background job"):
        await CeleryEventPublisher(celery_app).publish(object())  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("environment", "flag", "expected"),
    [
        ("development", None, True),
        ("production", None, False),
        ("production", True, True),
        ("development", False, False),
    ],
)
def test_api_docs_are_published_everywhere_but_production_unless_configured(
    environment: str, flag: bool | None, expected: bool
) -> None:
    settings = Settings(
        environment=environment,
        jwt_secret=SecretStr("x" * 32),
        api_docs_enabled=flag,
    )
    assert settings.publishes_api_docs is expected
