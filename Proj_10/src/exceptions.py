class ModerationServiceError(Exception):
    """Base exception for ReviewDesk comment moderation service."""
    pass


class ValidationError(ModerationServiceError):
    """Raised when request payload or parameters fail validation."""
    pass


class UserBlockedError(ModerationServiceError):
    """Raised when a blocked/banned user attempts to create or edit comments."""
    pass


class CommentNotFoundError(ModerationServiceError):
    """Raised when a requested comment ID does not exist."""
    pass


class UnauthorizedError(ModerationServiceError):
    """Raised when an operation violates resource ownership (e.g., editing someone else's comment)."""
    pass


class ContentRejectedError(ModerationServiceError):
    """Raised when submitted content fails moderation checks."""

    def __init__(self, message: str, reason: str = "", current_strikes: int = 0, is_blocked: bool = False):
        super().__init__(message)
        self.reason = reason
        self.current_strikes = current_strikes
        self.is_blocked = is_blocked


class CheckerExecutionError(ModerationServiceError):
    """Raised when the external content checker fails (network timeout, internal error, etc.)."""
    pass
