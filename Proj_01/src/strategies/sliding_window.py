import time
import threading
from collections import deque
from typing import Optional, Deque, Tuple
from .base import RateLimitStrategy
from ..models import RateLimitConfig, RateLimitResult


class SlidingWindowStrategy(RateLimitStrategy):
    """In-memory Sliding Window Log rate limiter.

    Tracks timestamps of admitted requests within a moving window. Provides exact
    rate limiting without window boundary bursts.
    """

    def __init__(self, config: RateLimitConfig):
        super().__init__(config)
        self._lock = threading.Lock()
        # Deque of (timestamp, token_count)
        self._requests: Deque[Tuple[float, int]] = deque()
        self._current_tokens: int = 0

    def _evict_expired(self, current_time: float) -> None:
        boundary = current_time - self.config.window_seconds
        while self._requests and self._requests[0][0] <= boundary:
            _, count = self._requests.popleft()
            self._current_tokens -= count

    def acquire(self, tokens: int = 1, current_time: Optional[float] = None) -> RateLimitResult:
        if tokens <= 0:
            raise ValueError(f"Tokens must be positive, got {tokens}")

        now = time.time() if current_time is None else float(current_time)

        with self._lock:
            self._evict_expired(now)

            # If request asks for more than total bucket capacity
            if tokens > self.config.capacity:
                return RateLimitResult(
                    allowed=False,
                    remaining_capacity=float(max(0, self.config.capacity - self._current_tokens)),
                    retry_after_seconds=float("inf"),
                    reset_time_seconds=float("inf")
                )

            # Check if capacity allows new tokens
            if self._current_tokens + tokens <= self.config.capacity:
                self._requests.append((now, tokens))
                self._current_tokens += tokens
                remaining = self.config.capacity - self._current_tokens

                # Reset time is when the oldest active request expires
                reset_after = (self._requests[0][0] + self.config.window_seconds - now) if self._requests else 0.0

                return RateLimitResult(
                    allowed=True,
                    remaining_capacity=float(remaining),
                    retry_after_seconds=0.0,
                    reset_time_seconds=max(0.0, float(reset_after))
                )

            # Capacity exceeded - calculate recovery time
            remaining = max(0, self.config.capacity - self._current_tokens)
            deficit = (self._current_tokens + tokens) - self.config.capacity

            accumulated_released = 0
            retry_after = self.config.window_seconds
            for ts, count in self._requests:
                accumulated_released += count
                if accumulated_released >= deficit:
                    retry_after = max(0.0, ts + self.config.window_seconds - now)
                    break

            oldest_ts = self._requests[0][0] if self._requests else now
            reset_after = max(0.0, oldest_ts + self.config.window_seconds - now)

            return RateLimitResult(
                allowed=False,
                remaining_capacity=float(remaining),
                retry_after_seconds=float(retry_after),
                reset_time_seconds=float(reset_after)
            )
