"""Comments & Replies - In-Memory Thread-Safe Discussion Service.

Enforces a strict two-level discussion hierarchy (Post -> Comment -> Reply)
with independent auto-incrementing ID sequences, complete post isolation,
defensive copy snapshots, and concurrency safety.
"""

from .exceptions import (
    CommentNotFoundError,
    CommentServiceError,
    ConflictError,
    InvalidHierarchyError,
    PostNotFoundError,
    ResourceNotFoundError,
    ValidationError,
)
from .models import Comment, Reply
from .service import CommentService

__all__ = [
    "CommentService",
    "Comment",
    "Reply",
    "CommentServiceError",
    "ValidationError",
    "ResourceNotFoundError",
    "PostNotFoundError",
    "CommentNotFoundError",
    "InvalidHierarchyError",
    "ConflictError",
]
