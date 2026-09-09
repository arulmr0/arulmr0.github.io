"""Domain exceptions. Services raise these; the API layer maps them to HTTP responses."""


class DomainError(Exception):
    status_code = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    status_code = 404


class ConflictError(DomainError):
    status_code = 409


class ValidationError(DomainError):
    status_code = 422


class InvalidTransitionError(ConflictError):
    """Raised when a state machine transition is not allowed."""

    def __init__(self, entity: str, current: str, target: str):
        super().__init__(f"{entity} cannot move from {current} to {target}")
