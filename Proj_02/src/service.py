"""Thread-safe, in-memory Comment and Reply discussion service.

Enforces:
- Strict two-level discussion hierarchy (Post -> Comment -> Reply).
- Independent auto-incrementing ID generators for comments and replies.
- Complete state isolation across distinct posts.
- Preservation of creation order independently of system timestamps.
- Defensive copy snapshots on all read operations to prevent state corruption.
- Thread-safe concurrency via reentrant locking (threading.RLock).
"""

from __future__ import annotations

import copy
import threading
import time
from typing import Any, Dict, List, Optional

from .exceptions import (
    CommentNotFoundError,
    InvalidHierarchyError,
    PostNotFoundError,
    ResourceNotFoundError,
    ValidationError,
)
from .models import Comment, Reply


class CommentService:
    """Core in-memory discussion service supporting comments and replies."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._comment_id_seq: int = 1
        self._reply_id_seq: int = 1

        # State storage
        self._post_comments: Dict[str, List[Comment]] = {}
        self._comments_by_id: Dict[int, Comment] = {}
        self._replies_by_id: Dict[int, Reply] = {}

    # -------------------------------------------------------------------------
    # Validation Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _validate_non_empty_string(value: Any, field_name: str) -> str:
        """Validate that a field is a non-empty, non-whitespace string."""
        if isinstance(value, bool) or not isinstance(value, str):
            raise ValidationError(
                f"Field '{field_name}' must be a string, received {type(value).__name__}."
            )
        cleaned = value.strip()
        if not cleaned:
            raise ValidationError(f"Field '{field_name}' cannot be empty or whitespace-only.")
        return cleaned

    @staticmethod
    def _validate_positive_int(value: Any, field_name: str) -> int:
        """Validate that an ID is a strictly positive integer, rejecting bools."""
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValidationError(
                f"Field '{field_name}' must be an integer, received {type(value).__name__}."
            )
        if value <= 0:
            raise ValidationError(f"Field '{field_name}' must be greater than 0, received {value}.")
        return value

    # -------------------------------------------------------------------------
    # Core Operations
    # -------------------------------------------------------------------------

    def add_comment(self, post_id: str, author_id: str, content: str) -> Comment:
        """Add a top-level comment to a post.

        Args:
            post_id: Identifier of the post to comment on.
            author_id: Identifier of the author creating the comment.
            content: Text body of the comment.

        Returns:
            A defensive copy of the newly created Comment.
        """
        valid_post_id = self._validate_non_empty_string(post_id, "post_id")
        valid_author_id = self._validate_non_empty_string(author_id, "author_id")
        valid_content = self._validate_non_empty_string(content, "content")

        with self._lock:
            comment_id = self._comment_id_seq
            self._comment_id_seq += 1

            comment = Comment(
                id=comment_id,
                post_id=valid_post_id,
                author_id=valid_author_id,
                content=valid_content,
                created_at=time.time(),
                replies=[],
            )

            if valid_post_id not in self._post_comments:
                self._post_comments[valid_post_id] = []

            self._post_comments[valid_post_id].append(comment)
            self._comments_by_id[comment_id] = comment

            return comment.copy()

    def add_reply(
        self,
        comment_id: int,
        author_id: str,
        content: str,
        post_id: Optional[str] = None,
        target_type: str = "comment",
    ) -> Reply:
        """Add a reply to an existing comment.

        Enforces the two-level hierarchy constraint:
        - Discussions are strictly Post -> Comment -> Reply.
        - Replies cannot be replied to.

        Args:
            comment_id: The ID of the parent comment.
            author_id: Identifier of the author creating the reply.
            content: Text body of the reply.
            post_id: Optional post identifier to verify parent-child relationship.
            target_type: Target entity type (defaults to 'comment').

        Returns:
            A defensive copy of the newly created Reply.

        Raises:
            ValidationError: If inputs are invalid.
            InvalidHierarchyError: If attempting to reply to a reply.
            CommentNotFoundError: If the target comment does not exist.
        """
        if str(target_type).lower() == "reply":
            raise InvalidHierarchyError(
                f"Cannot reply to reply ID {comment_id}. "
                "Discussions are strictly limited to two levels: Post -> Comment -> Reply."
            )

        valid_comment_id = self._validate_positive_int(comment_id, "comment_id")
        valid_author_id = self._validate_non_empty_string(author_id, "author_id")
        valid_content = self._validate_non_empty_string(content, "content")
        valid_post_id = (
            self._validate_non_empty_string(post_id, "post_id") if post_id is not None else None
        )

        with self._lock:
            # Check if parent comment exists
            if valid_comment_id not in self._comments_by_id:
                raise CommentNotFoundError(
                    f"Parent comment with ID {valid_comment_id} does not exist."
                )

            parent_comment = self._comments_by_id[valid_comment_id]

            # Verify post_id consistency if provided
            if valid_post_id is not None and parent_comment.post_id != valid_post_id:
                raise ValidationError(
                    f"Comment {valid_comment_id} belongs to post '{parent_comment.post_id}', "
                    f"not '{valid_post_id}'."
                )

            reply_id = self._reply_id_seq
            self._reply_id_seq += 1

            reply = Reply(
                id=reply_id,
                comment_id=valid_comment_id,
                post_id=parent_comment.post_id,
                author_id=valid_author_id,
                content=valid_content,
                created_at=time.time(),
            )

            parent_comment.replies.append(reply)
            self._replies_by_id[reply_id] = reply

            return copy.deepcopy(reply)

    def add_reply_to_reply(self, reply_id: int, author_id: str, content: str) -> None:
        """Explicitly reject attempts to add a reply to an existing reply."""
        raise InvalidHierarchyError(
            f"Cannot reply to reply ID {reply_id}. "
            "Discussions are strictly limited to two levels: Post -> Comment -> Reply."
        )

    def get_comment(self, comment_id: int) -> Comment:
        """Retrieve a specific comment and all its nested replies.

        Returns a defensive copy snapshot.
        """
        valid_comment_id = self._validate_positive_int(comment_id, "comment_id")
        with self._lock:
            if valid_comment_id not in self._comments_by_id:
                raise CommentNotFoundError(
                    f"Comment with ID {valid_comment_id} does not exist."
                )
            return self._comments_by_id[valid_comment_id].copy()

    def get_reply(self, reply_id: int) -> Reply:
        """Retrieve a specific reply by its independent reply ID.

        Returns a defensive copy snapshot.
        """
        valid_reply_id = self._validate_positive_int(reply_id, "reply_id")
        with self._lock:
            if valid_reply_id not in self._replies_by_id:
                raise ResourceNotFoundError(
                    f"Reply with ID {valid_reply_id} does not exist."
                )
            return copy.deepcopy(self._replies_by_id[valid_reply_id])

    def get_comments_for_post(self, post_id: str) -> List[Comment]:
        """Retrieve all comments and nested replies for a post in creation order.

        Returns deep copies of all comments.
        """
        valid_post_id = self._validate_non_empty_string(post_id, "post_id")
        with self._lock:
            comments = self._post_comments.get(valid_post_id, [])
            return [c.copy() for c in comments]

    def get_thread(self, post_id: str) -> List[Comment]:
        """Alias for get_comments_for_post."""
        return self.get_comments_for_post(post_id)

    def get_replies_for_comment(self, comment_id: int) -> List[Reply]:
        """Retrieve all replies for a specific comment in creation order.

        Returns deep copies of all replies.
        """
        valid_comment_id = self._validate_positive_int(comment_id, "comment_id")
        with self._lock:
            if valid_comment_id not in self._comments_by_id:
                raise CommentNotFoundError(
                    f"Comment with ID {valid_comment_id} does not exist."
                )
            return [copy.deepcopy(r) for r in self._comments_by_id[valid_comment_id].replies]

    def get_stats(self) -> Dict[str, int]:
        """Retrieve aggregated platform metrics."""
        with self._lock:
            return {
                "total_posts": len(self._post_comments),
                "total_comments": len(self._comments_by_id),
                "total_replies": len(self._replies_by_id),
            }

    def clear(self) -> None:
        """Reset all internal state and sequences (useful for test isolation)."""
        with self._lock:
            self._comment_id_seq = 1
            self._reply_id_seq = 1
            self._post_comments.clear()
            self._comments_by_id.clear()
            self._replies_by_id.clear()
