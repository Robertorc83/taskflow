from taskmanager.application.dto import RegisterUserCommand, TokenPair, UserDTO
from taskmanager.application.exceptions import (
    AuthenticationError,
    ConflictError,
    InvalidInputError,
)
from taskmanager.application.ports import (
    Clock,
    PasswordHasher,
    TokenService,
    TokenType,
    UnitOfWork,
)
from taskmanager.domain.entities import User
from taskmanager.domain.entities.user import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH

INVALID_CREDENTIALS = "Invalid email or password"


class RegisterUser:
    def __init__(self, uow: UnitOfWork, hasher: PasswordHasher, clock: Clock) -> None:
        self._uow = uow
        self._hasher = hasher
        self._clock = clock

    async def execute(self, command: RegisterUserCommand) -> UserDTO:
        if not PASSWORD_MIN_LENGTH <= len(command.password) <= PASSWORD_MAX_LENGTH:
            raise InvalidInputError(
                f"Password must be {PASSWORD_MIN_LENGTH}-{PASSWORD_MAX_LENGTH} characters",
                field="password",
            )
        async with self._uow as uow:
            if await uow.users.get_by_email(User.normalize_email(command.email)):
                raise ConflictError("A user with this email already exists")
            user = User.register(
                email=command.email,
                full_name=command.full_name,
                hashed_password=self._hasher.hash(command.password),
                now=self._clock.now(),
            )
            await uow.users.add(user)
            await uow.commit()
        return UserDTO.from_entity(user)


class AuthenticateUser:
    """Exchange credentials for tokens (SPEC-001 R4, R5)."""

    def __init__(self, uow: UnitOfWork, hasher: PasswordHasher, tokens: TokenService) -> None:
        self._uow = uow
        self._hasher = hasher
        self._tokens = tokens

    async def execute(self, email: str, password: str) -> TokenPair:
        async with self._uow as uow:
            user = await uow.users.get_by_email(User.normalize_email(email))
        if user is None:
            # Spend the same time as a real check so response timing doesn't reveal accounts.
            self._hasher.hash(password)
            raise AuthenticationError(INVALID_CREDENTIALS)
        if not self._hasher.verify(password, user.hashed_password) or not user.is_active:
            raise AuthenticationError(INVALID_CREDENTIALS)
        return self._tokens.issue(user.id)


class RefreshTokens:
    def __init__(self, uow: UnitOfWork, tokens: TokenService) -> None:
        self._uow = uow
        self._tokens = tokens

    async def execute(self, refresh_token: str) -> TokenPair:
        user_id = self._tokens.verify(refresh_token, TokenType.REFRESH)
        async with self._uow as uow:
            user = await uow.users.get(user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("Invalid token")
        return self._tokens.issue(user.id)


class AuthenticateAccessToken:
    """Resolve the user behind an access token, rejecting deactivated accounts."""

    def __init__(self, uow: UnitOfWork, tokens: TokenService) -> None:
        self._uow = uow
        self._tokens = tokens

    async def execute(self, access_token: str) -> UserDTO:
        user_id = self._tokens.verify(access_token, TokenType.ACCESS)
        async with self._uow as uow:
            user = await uow.users.get(user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("Invalid token")
        return UserDTO.from_entity(user)
