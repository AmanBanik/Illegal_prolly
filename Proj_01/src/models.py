from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class StrategyType(Enum):
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"


@dataclass(frozen=True)
class RateLimitConfig:
    """Configuration for a rate limiting rule.

    For Sliding Window:
        - `capacity`: Maximum number of requests allowed within `window_seconds`.
        - `window_seconds`: The duration of the sliding window in seconds.

    For Token Bucket:
        - `capacity`: Maximum bucket capacity (burst limit).
        - `refill_rate`: Tokens added per second. Defaults to capacity / window_seconds if omitted.
        - `window_seconds`: Used to calculate refill rate if refill_rate is not explicitly set.
    """
    capacity: int
    window_seconds: float
    refill_rate: Optional[float] = None

    def get_refill_rate(self) -> float:
        if self.refill_rate is not None and self.refill_rate > 0:
            return float(self.refill_rate)
        return float(self.capacity) / float(self.window_seconds)


@dataclass(frozen=True)
class RateLimitResult:
    """Result of an evaluation against the rate limiter."""
    allowed: bool
    remaining_capacity: float
    retry_after_seconds: float
    reset_time_seconds: float


@dataclass
class RateLimiterStats:
    """Snapshot of rate limiter statistics."""
    total_requests: int = 0
    allowed_requests: int = 0
    rejected_requests: int = 0
