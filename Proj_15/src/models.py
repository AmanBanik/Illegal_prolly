from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """User account entity inside the storage boundary."""
    user_id: str
    email: str
    password_hash: str
    created_at: datetime
    updated_at: datetime


@dataclass
class ResetCodeRecord:
    """Represents a time-bounded, single-use password reset code."""
    code: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    is_used: bool = False
    failed_attempts: int = 0


@dataclass(frozen=True)
class ResetRequestResponse:
    """API contract returned when a password reset is initiated."""
    reset_url: str
    reset_code: str
    expires_at: datetime
    validity_seconds: float
