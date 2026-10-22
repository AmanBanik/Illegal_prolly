"""Custom domain exceptions for the Comments & Replies service."""


class CommentServiceError(Exception):
    """Base exception for all domain errors within the comment service."""


class ValidationError(CommentServiceError):
    """Raised when input parameters fail type or value validation rules."""


class ResourceNotFoundError(CommentServiceError):
    """Raised when a requested resource (post or comment) does not exist."""


class PostNotFoundError(ResourceNotFoundError):
    """Raised when a post ID is not found or recognized."""


class CommentNotFoundError(ResourceNotFoundError):
    """Raised when a parent comment ID cannot be found."""


class InvalidHierarchyError(CommentServiceError):
    """Raised when attempting an invalid hierarchy operation (e.g., replying to a reply)."""


class ConflictError(CommentServiceError):
    """Raised when a resource or state conflict occurs."""
