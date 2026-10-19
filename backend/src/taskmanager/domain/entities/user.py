import re
from dataclasses import dataclass
from datetime import datetime
from typing import Self
from uuid import UUID, uuid4

from taskmanager.domain.exceptions import InvalidEmailError, InvalidFullNameError

FULL_NAME_MAX_LENGTH = 100
# Deliberately loose: full RFC 5322 validation happens at the API boundary.
_EMAIL_SHAPE = re.compile(r"^[^@\s]+@[^@\s]+$")


@dataclass(kw_only=True)
class User:
    id: UUID
    email: str
    full_name: str
    hashed_password: str
    is_active: bool
    created_at: datetime

    @classmethod
    def register(cls, *, email: str, full_name: str, hashed_password: str, now: datetime) -> Self:
        email = cls.normalize_email(email)
        if not _EMAIL_SHAPE.match(email):
            raise InvalidEmailError("Invalid email address")
        full_name = full_name.strip()
        if not 1 <= len(full_name) <= FULL_NAME_MAX_LENGTH:
            raise InvalidFullNameError(f"Full name must be 1-{FULL_NAME_MAX_LENGTH} characters")
        return cls(
            id=uuid4(),
            email=email,
            full_name=full_name,
            hashed_password=hashed_password,
            is_active=True,
            created_at=now,
        )

    @staticmethod
    def normalize_email(email: str) -> str:
        return email.strip().lower()

    def deactivate(self) -> None:
        self.is_active = False
