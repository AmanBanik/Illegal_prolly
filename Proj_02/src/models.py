"""Domain models representing two-level discussion structures (Comment and Reply)."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List

from .exceptions import InvalidHierarchyError


@dataclass
class Reply:
    """Represents a leaf-level reply to an existing comment.

    Discussions are strictly two-level (Post -> Comment -> Reply).
    Replies cannot have nested replies.
    """

    id: int
    comment_id: int
    post_id: str
    author_id: str
    content: str
    created_at: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialize reply to a primitive dictionary."""
        return {
            "id": self.id,
            "comment_id": self.comment_id,
            "post_id": self.post_id,
            "author_id": self.author_id,
            "content": self.content,
            "created_at": self.created_at,
        }

    def add_reply(self, *args: Any, **kwargs: Any) -> None:
        """Enforce strict two-level discussion hierarchy constraint."""
        raise InvalidHierarchyError(
            "Cannot reply to a reply. Discussions are strictly limited to two levels: Post -> Comment -> Reply."
        )


@dataclass
class Comment:
    """Represents a top-level comment directly under a post."""

    id: int
    post_id: str
    author_id: str
    content: str
    created_at: float
    replies: List[Reply] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize comment and nested replies to a primitive dictionary."""
        return {
            "id": self.id,
            "post_id": self.post_id,
            "author_id": self.author_id,
            "content": self.content,
            "created_at": self.created_at,
            "replies": [reply.to_dict() for reply in self.replies],
        }

    def copy(self) -> Comment:
        """Create an isolated deep copy of the comment and its replies."""
        return copy.deepcopy(self)
