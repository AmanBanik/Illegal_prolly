from abc import ABC, abstractmethod
from typing import Optional
from ..models import RateLimitConfig, RateLimitResult


class RateLimitStrategy(ABC):
    """Abstract base class for rate limiting algorithms."""

    def __init__(self, config: RateLimitConfig):
        self.config = config

    @abstractmethod
    def acquire(self, tokens: int = 1, current_time: Optional[float] = None) -> RateLimitResult:
        """Attempt to acquire tokens at `current_time`.

        Args:
            tokens: Number of tokens/requests to consume.
            current_time: Epoch timestamp in seconds. If None, time.time() is used.

        Returns:
            RateLimitResult containing whether request was allowed, remaining capacity,
            and estimated recovery/retry time.
        """
        pass
