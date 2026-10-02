"""
Domain exceptions raised by the service layer.

These are plain Python exceptions with no FastAPI dependency, so services
can be unit-tested without spinning up the web framework at all. A single
set of exception handlers (registered in app/main.py) translates these
into the right HTTP status codes at the edge of the app.
"""


class AppError(Exception):
    """Base class for all domain errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class NotFoundError(AppError):
    """Resource doesn't exist, or the caller has no right to know it does."""

    pass


class ForbiddenError(AppError):
    """Caller is authenticated but not allowed to perform this action."""

    pass


class ConflictError(AppError):
    """Request is well-formed but violates current state (e.g. bad transition)."""

    pass


class BadRequestError(AppError):
    """Request violates a business rule not covered by schema validation."""

    pass


class AuthenticationError(AppError):
    """Login/credential/token failure."""

    pass
