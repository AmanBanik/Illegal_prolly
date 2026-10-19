import time
import threading
from typing import Optional
from .base import RateLimitStrategy
from ..models import RateLimitConfig, RateLimitResult


class TokenBucketStrategy(RateLimitStrategy):
    """In-memory Token Bucket rate limiter.

    Allows burst traffic up to `capacity` while smoothly refilling tokens
    at a continuous rate (`refill_rate` tokens per second).
    """

    def __init__(self, config: RateLimitConfig):
        super().__init__(config)
        self._lock = threading.Lock()
        self._capacity = float(config.capacity)
        self._refill_rate = config.get_refill_rate()
        self._tokens = float(config.capacity)
        self._last_refill_time: Optional[float] = None

    def _refill(self, current_time: float) -> None:
        if self._last_refill_time is None:
            self._last_refill_time = current_time
            return

        elapsed = current_time - self._last_refill_time
        if elapsed > 0:
            added_tokens = elapsed * self._refill_rate
            self._tokens = min(self._capacity, self._tokens + added_tokens)
            self._last_refill_time = current_time

    def acquire(self, tokens: int = 1, current_time: Optional[float] = None) -> RateLimitResult:
        if tokens <= 0:
            raise ValueError(f"Tokens must be positive, got {tokens}")

        now = time.time() if current_time is None else float(current_time)

        with self._lock:
            self._refill(now)

            if tokens > self._capacity:
                return RateLimitResult(
                    allowed=False,
                    remaining_capacity=float(self._tokens),
                    retry_after_seconds=float("inf"),
                    reset_time_seconds=float("inf")
                )

            if self._tokens >= tokens:
                self._tokens -= float(tokens)
                time_to_full = (self._capacity - self._tokens) / self._refill_rate if self._refill_rate > 0 else 0.0
                return RateLimitResult(
                    allowed=True,
                    remaining_capacity=float(self._tokens),
                    retry_after_seconds=0.0,
                    reset_time_seconds=max(0.0, float(time_to_full))
                )

            # Deficit
            deficit = float(tokens) - self._tokens
            retry_after = deficit / self._refill_rate if self._refill_rate > 0 else float("inf")
            time_to_full = (self._capacity - self._tokens) / self._refill_rate if self._refill_rate > 0 else float("inf")

            return RateLimitResult(
                allowed=False,
                remaining_capacity=float(self._tokens),
                retry_after_seconds=max(0.0, float(retry_after)),
                reset_time_seconds=max(0.0, float(time_to_full))
            )
