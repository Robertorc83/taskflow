"""Use-case level failures, independent of any delivery mechanism."""


class ApplicationError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(ApplicationError):
    pass


class PermissionDeniedError(ApplicationError):
    pass


class ConflictError(ApplicationError):
    pass


class InvalidInputError(ApplicationError):
    def __init__(self, message: str, *, field: str | None = None) -> None:
        super().__init__(message)
        self.field = field


class AuthenticationError(ApplicationError):
    pass
