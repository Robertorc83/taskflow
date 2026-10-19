from datetime import timedelta
from uuid import UUID, uuid4

import jwt

from taskmanager.application.dto import TokenPair
from taskmanager.application.exceptions import AuthenticationError
from taskmanager.application.ports import Clock, TokenType


class JwtTokenService:
    """HS256 JWTs carrying `sub`, `type`, `iat`, `exp` and `jti` (SPEC-001 R6, R7)."""

    def __init__(
        self,
        *,
        secret: str,
        clock: Clock,
        algorithm: str = "HS256",
        access_ttl: timedelta = timedelta(minutes=15),
        refresh_ttl: timedelta = timedelta(days=7),
    ) -> None:
        self._secret = secret
        self._clock = clock
        self._algorithm = algorithm
        self._ttl = {TokenType.ACCESS: access_ttl, TokenType.REFRESH: refresh_ttl}

    def issue(self, user_id: UUID) -> TokenPair:
        return TokenPair(
            access_token=self._encode(user_id, TokenType.ACCESS),
            refresh_token=self._encode(user_id, TokenType.REFRESH),
            expires_in=int(self._ttl[TokenType.ACCESS].total_seconds()),
        )

    def verify(self, token: str, expected_type: TokenType) -> UUID:
        try:
            claims = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                options={"require": ["sub", "type", "exp", "iat"]},
            )
            if claims["type"] != expected_type.value:
                raise AuthenticationError("Invalid token type")
            return UUID(claims["sub"])
        except (jwt.PyJWTError, ValueError) as error:
            raise AuthenticationError("Invalid or expired token") from error

    def _encode(self, user_id: UUID, token_type: TokenType) -> str:
        now = self._clock.now()
        claims = {
            "sub": str(user_id),
            "type": token_type.value,
            "iat": now,
            "exp": now + self._ttl[token_type],
            "jti": uuid4().hex,
        }
        return jwt.encode(claims, self._secret, algorithm=self._algorithm)
