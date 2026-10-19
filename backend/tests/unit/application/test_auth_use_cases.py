from uuid import uuid4

import pytest

from taskmanager.application.dto import PageRequest, RegisterUserCommand
from taskmanager.application.exceptions import (
    AuthenticationError,
    ConflictError,
    InvalidInputError,
)
from taskmanager.application.use_cases.auth import (
    AuthenticateAccessToken,
    AuthenticateUser,
    RefreshTokens,
    RegisterUser,
)
from taskmanager.application.use_cases.users import ListUsers
from tests.fakes import FakeTokenService, FixedClock, InMemoryUnitOfWork, PlainTextPasswordHasher
from tests.unit.application.conftest import UserFactory


class TestRegisterUser:
    async def test_registers_a_user_with_a_hashed_password(
        self, uow: InMemoryUnitOfWork, hasher: PlainTextPasswordHasher, clock: FixedClock
    ) -> None:
        command = RegisterUserCommand("Carol@Example.com", "Carol Diaz", "Secret123!")

        user = await RegisterUser(uow, hasher, clock).execute(command)

        stored = await uow.users.get(user.id)
        assert stored is not None
        assert stored.email == "carol@example.com"
        assert stored.hashed_password == hasher.hash("Secret123!")
        assert uow.commits == 1

    async def test_rejects_an_email_that_is_already_taken_in_any_case(
        self,
        uow: InMemoryUnitOfWork,
        hasher: PlainTextPasswordHasher,
        clock: FixedClock,
        make_user: UserFactory,
    ) -> None:
        await make_user("alice@example.com")

        with pytest.raises(ConflictError):
            await RegisterUser(uow, hasher, clock).execute(
                RegisterUserCommand("ALICE@example.com", "Alice", "Secret123!")
            )


class TestAuthenticateUser:
    async def test_valid_credentials_return_tokens(
        self,
        uow: InMemoryUnitOfWork,
        hasher: PlainTextPasswordHasher,
        tokens: FakeTokenService,
        make_user: UserFactory,
    ) -> None:
        user = await make_user("alice@example.com", password="Alice123!")

        pair = await AuthenticateUser(uow, hasher, tokens).execute(
            " Alice@example.com", "Alice123!"
        )

        assert pair.access_token == f"access:{user.id}"

    @pytest.mark.parametrize(
        ("email", "password"),
        [("alice@example.com", "wrong"), ("ghost@example.com", "Alice123!")],
    )
    async def test_wrong_password_and_unknown_email_fail_identically(
        self,
        uow: InMemoryUnitOfWork,
        hasher: PlainTextPasswordHasher,
        tokens: FakeTokenService,
        make_user: UserFactory,
        email: str,
        password: str,
    ) -> None:
        await make_user("alice@example.com", password="Alice123!")

        with pytest.raises(AuthenticationError, match="Invalid email or password"):
            await AuthenticateUser(uow, hasher, tokens).execute(email, password)

    async def test_inactive_users_cannot_log_in(
        self,
        uow: InMemoryUnitOfWork,
        hasher: PlainTextPasswordHasher,
        tokens: FakeTokenService,
        make_user: UserFactory,
    ) -> None:
        await make_user("alice@example.com", password="Alice123!", active=False)

        with pytest.raises(AuthenticationError):
            await AuthenticateUser(uow, hasher, tokens).execute("alice@example.com", "Alice123!")


class TestTokens:
    async def test_refresh_issues_a_new_pair(
        self, uow: InMemoryUnitOfWork, tokens: FakeTokenService, make_user: UserFactory
    ) -> None:
        user = await make_user("alice@example.com")

        pair = await RefreshTokens(uow, tokens).execute(f"refresh:{user.id}")

        assert pair.refresh_token == f"refresh:{user.id}"

    async def test_refresh_rejects_access_tokens(
        self, uow: InMemoryUnitOfWork, tokens: FakeTokenService, make_user: UserFactory
    ) -> None:
        user = await make_user("alice@example.com")

        with pytest.raises(AuthenticationError):
            await RefreshTokens(uow, tokens).execute(f"access:{user.id}")

    @pytest.mark.parametrize("use_case", [RefreshTokens, AuthenticateAccessToken])
    async def test_tokens_of_unknown_or_inactive_users_are_rejected(
        self,
        uow: InMemoryUnitOfWork,
        tokens: FakeTokenService,
        make_user: UserFactory,
        use_case: type[RefreshTokens] | type[AuthenticateAccessToken],
    ) -> None:
        inactive = await make_user("alice@example.com", active=False)
        kind = "refresh" if use_case is RefreshTokens else "access"

        for user_id in (inactive.id, uuid4()):
            with pytest.raises(AuthenticationError):
                await use_case(uow, tokens).execute(f"{kind}:{user_id}")

    async def test_access_token_resolves_the_current_user(
        self, uow: InMemoryUnitOfWork, tokens: FakeTokenService, make_user: UserFactory
    ) -> None:
        user = await make_user("alice@example.com")

        current = await AuthenticateAccessToken(uow, tokens).execute(f"access:{user.id}")

        assert current.email == "alice@example.com"


async def test_list_users_is_paginated(uow: InMemoryUnitOfWork, make_user: UserFactory) -> None:
    for name in ("alice", "bob", "carol"):
        await make_user(f"{name}@example.com")

    page = await ListUsers(uow).execute(PageRequest(page=2, size=2))

    assert [u.email for u in page.items] == ["carol@example.com"]
    assert (page.total, page.pages) == (3, 2)


@pytest.mark.parametrize("password", ["short7!", "x" * 129])
async def test_password_length_is_a_use_case_rule(
    uow: InMemoryUnitOfWork, hasher: PlainTextPasswordHasher, clock: FixedClock, password: str
) -> None:
    """CR-006: SPEC-001 R2 holds for every caller, not only HTTP."""
    with pytest.raises(InvalidInputError) as error:
        await RegisterUser(uow, hasher, clock).execute(
            RegisterUserCommand("carol@example.com", "Carol", password)
        )
    assert error.value.field == "password"
    assert uow.users.rows == {}
