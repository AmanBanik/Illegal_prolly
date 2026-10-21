class ShortenerError(Exception):
    """Base exception for all URL shortener service errors."""
    status_code: int = 500

    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code


class ValidationError(ShortenerError):
    """Raised when request payload or parameters are invalid."""
    status_code: int = 400


class InvalidUrlError(ValidationError):
    """Raised when the target long URL is malformed or invalid."""
    status_code: int = 400


class InvalidShortCodeError(ValidationError):
    """Raised when custom short-code fails format constraints or uses reserved words."""
    status_code: int = 400


class CodeAlreadyExistsError(ShortenerError):
    """Raised when attempting to use a short-code that is already registered."""
    status_code: int = 409


class LinkNotFoundError(ShortenerError):
    """Raised when short code does not exist or has been deleted."""
    status_code: int = 404


class LinkExpiredError(ShortenerError):
    """Raised when short code has passed its TTL expiration date."""
    status_code: int = 410


class ForbiddenError(ShortenerError):
    """Raised when user does not have permission to delete or mutate the link."""
    status_code: int = 403


class CollisionExhaustionError(ShortenerError):
    """Raised when automated short-code generation exceeds max retry attempts."""
    status_code: int = 500
