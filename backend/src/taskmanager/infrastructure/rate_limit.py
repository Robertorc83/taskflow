"""Rate limiting (SPEC-006), built on the `limits` library with a moving-window strategy."""

import time
from math import ceil

from limits import parse
from limits.aio.strategies import MovingWindowRateLimiter
from limits.storage import storage_from_string


class RateLimitExceededError(Exception):
    def __init__(self, retry_after: int) -> None:
        super().__init__(f"Rate limit exceeded, retry in {retry_after}s")
        self.retry_after = retry_after


class RateLimiter:
    """Counts hits per (scope, key). Storage is Redis in production, memory in tests."""

    def __init__(
        self, storage_uri: str, *, auth_limit: str, api_limit: str, enabled: bool = True
    ) -> None:
        if not storage_uri.startswith("async+"):
            storage_uri = f"async+{storage_uri}"
        self._strategy = MovingWindowRateLimiter(storage_from_string(storage_uri))
        self._limits = {"auth": parse(auth_limit), "api": parse(api_limit)}
        self.enabled = enabled

    async def hit_auth(self, client_key: str) -> None:
        await self._hit("auth", client_key)

    async def hit_api(self, user_key: str) -> None:
        await self._hit("api", user_key)

    async def _hit(self, scope: str, key: str) -> None:
        if not self.enabled:
            return
        limit = self._limits[scope]
        if not await self._strategy.hit(limit, scope, key):
            stats = await self._strategy.get_window_stats(limit, scope, key)
            raise RateLimitExceededError(retry_after=max(1, ceil(stats.reset_time - time.time())))
