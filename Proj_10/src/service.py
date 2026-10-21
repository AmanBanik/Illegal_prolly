from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone
import threading
from typing import Dict, List, Optional
from .checker import ContentChecker
from .exceptions import (
    CheckerExecutionError,
    CommentNotFoundError,
    ContentRejectedError,
    ModerationServiceError,
    UnauthorizedError,
    UserBlockedError,
    ValidationError,
)
from .models import Comment, ModerationResult, UserState


class _InternalUserState:
    """Internal mutable tracking state for a user."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.strikes = 0
        self.is_blocked = False
        self.blocked_at: Optional[datetime] = None

    def to_snapshot(self) -> UserState:
        return UserState(
            user_id=self.user_id,
            strikes=self.strikes,
            is_blocked=self.is_blocked,
            blocked_at=self.blocked_at,
        )


class ReviewDesk:
    """Production-grade in-memory comment and moderation management service."""

    def __init__(
        self,
        checker: ContentChecker,
        max_strikes: int = 3,
        max_content_length: int = 5000,
    ):
        if checker is None:
            raise ValidationError("A valid ContentChecker instance must be provided")
        if max_strikes <= 0:
            raise ValidationError("max_strikes must be a positive integer")
        if max_content_length <= 0:
            raise ValidationError("max_content_length must be a positive integer")

        self._checker = checker
        self._max_strikes = max_strikes
        self._max_content_length = max_content_length

        self._lock = threading.RLock()
        self._next_comment_id = 1
        self._comments: Dict[int, Comment] = {}
        self._post_to_comment_ids: Dict[str, List[int]] = defaultdict(list)
        self._user_to_comment_ids: Dict[str, List[int]] = defaultdict(list)
        self._users: Dict[str, _InternalUserState] = {}

    @property
    def max_strikes(self) -> int:
        return self._max_strikes

    @property
    def max_content_length(self) -> int:
        return self._max_content_length

    def _validate_string_field(self, value: Optional[str], field_name: str) -> str:
        if value is None or not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a non-empty string")
        cleaned = value.strip()
        if not cleaned:
            raise ValidationError(f"{field_name} cannot be empty or whitespace only")
        return cleaned

    def _validate_content(self, content: Optional[str]) -> str:
        if content is None or not isinstance(content, str):
            raise ValidationError("Content must be a non-empty string")
        cleaned = content.strip()
        if not cleaned:
            raise ValidationError("Content cannot be empty or whitespace only")
        if len(content) > self._max_content_length:
            raise ValidationError(
                f"Content exceeds maximum allowable length of {self._max_content_length} characters"
            )
        return content

    def _get_or_create_user(self, user_id: str) -> _InternalUserState:
        if user_id not in self._users:
            self._users[user_id] = _InternalUserState(user_id)
        return self._users[user_id]

    def create_comment(
        self,
        post_id: str,
        user_id: str,
        content: str,
        current_time: Optional[datetime] = None,
    ) -> Comment:
        """Validates, moderates, and creates a published comment.

        Enforces the strict operation order:
        1. Input validation
        2. User block status check
        3. External content moderation (atomic rollback on failure)
        4. Strike accumulation / automatic blocking on rejection
        5. Monotonic sequential ID allocation and comment persistence on approval
        """
        valid_post_id = self._validate_string_field(post_id, "post_id")
        valid_user_id = self._validate_string_field(user_id, "user_id")
        valid_content = self._validate_content(content)

        now = current_time or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        with self._lock:
            user = self._get_or_create_user(valid_user_id)
            if user.is_blocked:
                raise UserBlockedError(
                    f"User '{valid_user_id}' is blocked from posting comments (strikes: {user.strikes})"
                )

            # Injected content checker invocation
            try:
                result = self._checker.check_content(valid_content)
            except Exception as e:
                # Failure isolation: leave ID allocation, reviews, and strikes unchanged
                if isinstance(e, ModerationServiceError):
                    raise
                raise CheckerExecutionError(f"Content checker service failed: {str(e)}") from e

            if not isinstance(result, ModerationResult):
                raise CheckerExecutionError("Checker must return a valid ModerationResult instance")

            if not result.is_approved:
                # Accumulate strike
                user.strikes += 1
                if user.strikes >= self._max_strikes:
                    user.is_blocked = True
                    user.blocked_at = now

                reason = result.reason or "Violated content moderation standards"
                raise ContentRejectedError(
                    message=f"Comment rejected by moderation checker: {reason}",
                    reason=reason,
                    current_strikes=user.strikes,
                    is_blocked=user.is_blocked,
                )

            # Content approved: allocate sequential monotonic ID
            comment_id = self._next_comment_id
            self._next_comment_id += 1

            new_comment = Comment(
                id=comment_id,
                post_id=valid_post_id,
                user_id=valid_user_id,
                content=valid_content,
                created_at=now,
                updated_at=now,
                is_edited=False,
            )

            self._comments[comment_id] = new_comment
            self._post_to_comment_ids[valid_post_id].append(comment_id)
            self._user_to_comment_ids[valid_user_id].append(comment_id)

            return deepcopy(new_comment)

    def edit_comment(
        self,
        comment_id: int,
        user_id: str,
        new_content: str,
        current_time: Optional[datetime] = None,
    ) -> Comment:
        """Edits an existing comment subject to ownership checks and moderation.

        If the checker fails, strikes and comment content are preserved.
        If rejected, a strike is recorded and the comment is not updated.
        """
        if not isinstance(comment_id, int) or comment_id <= 0:
            raise ValidationError("comment_id must be a positive integer")
        valid_user_id = self._validate_string_field(user_id, "user_id")
        valid_new_content = self._validate_content(new_content)

        now = current_time or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        with self._lock:
            user = self._get_or_create_user(valid_user_id)
            if user.is_blocked:
                raise UserBlockedError(
                    f"User '{valid_user_id}' is blocked from editing comments (strikes: {user.strikes})"
                )

            existing_comment = self._comments.get(comment_id)
            if existing_comment is None:
                raise CommentNotFoundError(f"Comment #{comment_id} does not exist")

            if existing_comment.user_id != valid_user_id:
                raise UnauthorizedError(
                    f"User '{valid_user_id}' is not authorized to edit comment #{comment_id}"
                )

            # Moderate new content
            try:
                result = self._checker.check_content(valid_new_content)
            except Exception as e:
                if isinstance(e, ModerationServiceError):
                    raise
                raise CheckerExecutionError(f"Content checker service failed: {str(e)}") from e

            if not isinstance(result, ModerationResult):
                raise CheckerExecutionError("Checker must return a valid ModerationResult instance")

            if not result.is_approved:
                user.strikes += 1
                if user.strikes >= self._max_strikes:
                    user.is_blocked = True
                    user.blocked_at = now

                reason = result.reason or "Violated content moderation standards"
                raise ContentRejectedError(
                    message=f"Edit rejected by moderation checker: {reason}",
                    reason=reason,
                    current_strikes=user.strikes,
                    is_blocked=user.is_blocked,
                )

            updated_comment = Comment(
                id=existing_comment.id,
                post_id=existing_comment.post_id,
                user_id=existing_comment.user_id,
                content=valid_new_content,
                created_at=existing_comment.created_at,
                updated_at=now,
                is_edited=True,
            )

            self._comments[comment_id] = updated_comment
            return deepcopy(updated_comment)

    def get_comment(self, comment_id: int) -> Comment:
        """Retrieves a defensive snapshot of a single comment by ID."""
        if not isinstance(comment_id, int) or comment_id <= 0:
            raise ValidationError("comment_id must be a positive integer")

        with self._lock:
            comment = self._comments.get(comment_id)
            if comment is None:
                raise CommentNotFoundError(f"Comment #{comment_id} does not exist")
            return deepcopy(comment)

    def list_comments(self, post_id: str) -> List[Comment]:
        """Lists all comments for a post in chronological creation order."""
        valid_post_id = self._validate_string_field(post_id, "post_id")
        with self._lock:
            comment_ids = self._post_to_comment_ids.get(valid_post_id, [])
            return [deepcopy(self._comments[cid]) for cid in comment_ids if cid in self._comments]

    def list_comments_by_user(self, user_id: str) -> List[Comment]:
        """Lists all comments authored by a specific user."""
        valid_user_id = self._validate_string_field(user_id, "user_id")
        with self._lock:
            comment_ids = self._user_to_comment_ids.get(valid_user_id, [])
            return [deepcopy(self._comments[cid]) for cid in comment_ids if cid in self._comments]

    def delete_comment(self, comment_id: int, user_id: str) -> bool:
        """Deletes a comment if the requesting user is the author."""
        if not isinstance(comment_id, int) or comment_id <= 0:
            raise ValidationError("comment_id must be a positive integer")
        valid_user_id = self._validate_string_field(user_id, "user_id")

        with self._lock:
            comment = self._comments.get(comment_id)
            if comment is None:
                raise CommentNotFoundError(f"Comment #{comment_id} does not exist")

            if comment.user_id != valid_user_id:
                raise UnauthorizedError(
                    f"User '{valid_user_id}' is not authorized to delete comment #{comment_id}"
                )

            del self._comments[comment_id]
            if comment.post_id in self._post_to_comment_ids:
                self._post_to_comment_ids[comment.post_id] = [
                    cid for cid in self._post_to_comment_ids[comment.post_id] if cid != comment_id
                ]
            if valid_user_id in self._user_to_comment_ids:
                self._user_to_comment_ids[valid_user_id] = [
                    cid for cid in self._user_to_comment_ids[valid_user_id] if cid != comment_id
                ]
            return True

    def get_user_state(self, user_id: str) -> UserState:
        """Retrieves a defensive snapshot of a user's strike and blocking status."""
        valid_user_id = self._validate_string_field(user_id, "user_id")
        with self._lock:
            user = self._get_or_create_user(valid_user_id)
            return user.to_snapshot()

    def unblock_user(self, user_id: str, reset_strikes: bool = True) -> UserState:
        """Administrative action: unblocks a user and optionally clears strikes."""
        valid_user_id = self._validate_string_field(user_id, "user_id")
        with self._lock:
            user = self._get_or_create_user(valid_user_id)
            user.is_blocked = False
            user.blocked_at = None
            if reset_strikes:
                user.strikes = 0
            return user.to_snapshot()

    def reset_user_strikes(self, user_id: str) -> UserState:
        """Administrative action: resets strikes to 0 for a user."""
        valid_user_id = self._validate_string_field(user_id, "user_id")
        with self._lock:
            user = self._get_or_create_user(valid_user_id)
            user.strikes = 0
            return user.to_snapshot()


# Alias for flexible test imports
CommentModerationService = ReviewDesk
