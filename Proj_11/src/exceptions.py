"""Domain exceptions for IssueHub Retry-Safe Issue Service."""


class IssueServiceError(Exception):
    """Base exception for all IssueHub service errors."""
    pass


class ValidationError(IssueServiceError):
    """Raised when input parameters fail validation constraints."""
    pass


class ProjectNotFoundError(IssueServiceError):
    """Raised when the specified project is not found."""
    pass


class IssueNotFoundError(IssueServiceError):
    """Raised when the specified issue is not found in the project."""
    pass


class AuthorizationError(IssueServiceError):
    """Raised when a user lacks required permissions for a project operation."""
    pass


class VersionConflictError(IssueServiceError):
    """Raised when optimistic concurrency control detects a version mismatch."""
    pass


class InvalidStatusTransitionError(IssueServiceError):
    """Raised when an issue status transition violates allowed workflow rules."""
    pass


class IdempotencyConflictError(IssueServiceError):
    """Raised when an idempotency key is reused with mismatched request parameters."""
    pass


class DuplicateProjectError(IssueServiceError):
    """Raised when attempting to create a project with an existing project_id."""
    pass
