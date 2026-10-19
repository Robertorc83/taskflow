"""Violations of business rules. The presentation layer maps them to HTTP status codes."""


class DomainError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidTaskTitleError(DomainError):
    pass


class InvalidTaskDescriptionError(DomainError):
    pass


class DueDateInPastError(DomainError):
    pass


class InvalidStatusTransitionError(DomainError):
    pass


class TaskAlreadyCompletedError(DomainError):
    pass


class InvalidEmailError(DomainError):
    pass


class InvalidFullNameError(DomainError):
    pass
