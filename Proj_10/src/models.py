from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class ModerationDecision(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class ModerationResult:
    """Immutable result emitted by a content moderation checker."""
    is_approved: bool
    reason: Optional[str] = None

    @classmethod
    def approved(cls) -> "ModerationResult":
        return cls(is_approved=True, reason=None)

    @classmethod
    def rejected(cls, reason: str = "Content violated community guidelines") -> "ModerationResult":
        return cls(is_approved=False, reason=reason)


@dataclass(frozen=True)
class UserState:
    """Defensive snapshot representing a user's violation and block status."""
    user_id: str
    strikes: int = 0
    is_blocked: bool = False
    blocked_at: Optional[datetime] = None


@dataclass(frozen=True)
class Comment:
    """Defensive snapshot of a published comment."""
    id: int
    post_id: str
    user_id: str
    content: str
    created_at: datetime
    updated_at: datetime
    is_edited: bool = False
