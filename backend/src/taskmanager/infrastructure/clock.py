from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from taskmanager.application.ports import Clock


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class ZonedClock:
    """The same instant, expressed in the user's time zone (CR-005).

    The domain derives "today" from `now().date()`, so this makes due-date checks and
    `is_overdue` follow the user's calendar. Timestamps remain timezone-aware instants.
    """

    def __init__(self, clock: Clock, zone: ZoneInfo) -> None:
        self._clock = clock
        self._zone = zone

    def now(self) -> datetime:
        return self._clock.now().astimezone(self._zone)
