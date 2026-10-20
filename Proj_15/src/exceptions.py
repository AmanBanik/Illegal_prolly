class PasswordResetError(Exception):
    """Base exception for all password reset service errors."""
    pass


class ConfigurationError(PasswordResetError):
    """Raised when service configuration is missing or malformed."""
    pass


class UserNotFoundError(PasswordResetError):
    """Raised when the target user does not exist."""
    pass


class InvalidCodeError(PasswordResetError):
    """Raised when an invalid or incorrect reset code is supplied."""
    pass


class ExpiredCodeError(PasswordResetError):
    """Raised when a reset code has exceeded its 30-second validity window."""
    pass


class CodeAlreadyUsedError(PasswordResetError):
    """Raised when an attempt is made to replay a previously consumed code."""
    pass


class RateLimitExceededError(PasswordResetError):
    """Raised when too many invalid attempts are made."""
    pass


class WeakPasswordError(PasswordResetError):
    """Raised when a new password does not meet security criteria."""
    pass
