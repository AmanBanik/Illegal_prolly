class ReturnGuardError(Exception):
    """Base exception for ReturnGuard risk assessment pipeline."""
    pass


class ValidationError(ReturnGuardError):
    """Raised when request payload or parameter types/ranges fail validation."""
    pass


class InvalidRatingError(ValidationError):
    """Raised when customer rating is non-numeric, a boolean, or out of range."""
    pass


class InvalidPurchaseValueError(ValidationError):
    """Raised when purchase value is non-numeric, a boolean, or negative."""
    pass


class InvalidAccountAgeError(ValidationError):
    """Raised when account age is non-integer, a boolean, or negative."""
    pass
