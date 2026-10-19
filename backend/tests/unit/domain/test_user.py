from datetime import UTC, datetime

import pytest

from taskmanager.domain.entities import User
from taskmanager.domain.exceptions import InvalidEmailError, InvalidFullNameError

NOW = datetime(2026, 10, 19, 9, 0, tzinfo=UTC)


def register(email: str = "alice@example.com", full_name: str = "Alice Smith") -> User:
    return User.register(email=email, full_name=full_name, hashed_password="hash", now=NOW)


def test_a_registered_user_is_active_with_normalized_email_and_name() -> None:
    user = register(email="  Alice@Example.COM ", full_name="  Alice Smith ")

    assert user.email == "alice@example.com"
    assert user.full_name == "Alice Smith"
    assert user.is_active
    assert user.created_at == NOW


@pytest.mark.parametrize("email", ["", "no-at-sign", "@example.com", "alice@"])
def test_email_must_look_like_an_address(email: str) -> None:
    with pytest.raises(InvalidEmailError):
        register(email=email)


@pytest.mark.parametrize("full_name", ["", "   ", "x" * 101])
def test_full_name_must_be_between_1_and_100_characters(full_name: str) -> None:
    with pytest.raises(InvalidFullNameError):
        register(full_name=full_name)


def test_a_user_can_be_deactivated() -> None:
    user = register()

    user.deactivate()

    assert not user.is_active


def test_normalize_email_is_reusable_for_lookups() -> None:
    assert User.normalize_email(" Bob@Example.com ") == "bob@example.com"
