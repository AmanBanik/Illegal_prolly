from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class LinkRecord:
    """Represents a persisted URL mapping in the database."""
    short_code: str
    original_url: str
    user_id: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    hit_count: int = 0
    is_deleted: bool = False

    def is_expired(self, current_time: Optional[datetime] = None) -> bool:
        if self.expires_at is None:
            return False
        now = current_time or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        record_exp = self.expires_at
        if record_exp.tzinfo is None:
            record_exp = record_exp.replace(tzinfo=timezone.utc)
        return now > record_exp

    def is_active(self, current_time: Optional[datetime] = None) -> bool:
        return (not self.is_deleted) and (not self.is_expired(current_time))


@dataclass(frozen=True)
class CreateLinkRequest:
    """Request payload for creating a new short link."""
    original_url: str
    user_id: str
    custom_code: Optional[str] = None
    ttl_seconds: Optional[int] = None


@dataclass(frozen=True)
class LinkMetadata:
    """Response contract for link details and statistics."""
    short_code: str
    original_url: str
    short_url: str
    user_id: str
    created_at: str
    expires_at: Optional[str]
    hit_count: int
    is_active: bool


@dataclass(frozen=True)
class AggregateStats:
    """System-wide or user-scoped aggregate statistics."""
    total_links: int
    active_links: int
    expired_links: int
    deleted_links: int
    total_hits: int
