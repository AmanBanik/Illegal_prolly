import pytest
from src.models import RateLimitConfig
from src.strategies.sliding_window import SlidingWindowStrategy


def test_sliding_window_basic_admit_and_reject():
    config = RateLimitConfig(capacity=3, window_seconds=10.0)
    limiter = SlidingWindowStrategy(config)

    t0 = 1000.0
    r1 = limiter.acquire(tokens=1, current_time=t0)
    assert r1.allowed is True
    assert r1.remaining_capacity == 2.0
    assert r1.retry_after_seconds == 0.0

    r2 = limiter.acquire(tokens=1, current_time=t0 + 1.0)
    assert r2.allowed is True
    assert r2.remaining_capacity == 1.0

    r3 = limiter.acquire(tokens=1, current_time=t0 + 2.0)
    assert r3.allowed is True
    assert r3.remaining_capacity == 0.0

    # 4th request within 10s should be rejected
    r4 = limiter.acquire(tokens=1, current_time=t0 + 3.0)
    assert r4.allowed is False
    assert r4.remaining_capacity == 0.0
    # First request was at 1000.0, so it expires at 1010.0. Current time is 1003.0 -> retry_after = 7.0s
    assert pytest.approx(r4.retry_after_seconds, 0.1) == 7.0


def test_sliding_window_expiration_and_recovery():
    config = RateLimitConfig(capacity=2, window_seconds=5.0)
    limiter = SlidingWindowStrategy(config)

    t0 = 100.0
    limiter.acquire(1, current_time=t0)
    limiter.acquire(1, current_time=t0 + 2.0)

    # At t0 + 4, rejected
    res = limiter.acquire(1, current_time=t0 + 4.0)
    assert res.allowed is False

    # At t0 + 5.1, the first request at t0 has expired (window is 5.0)
    res_after = limiter.acquire(1, current_time=t0 + 5.1)
    assert res_after.allowed is True
    assert res_after.remaining_capacity == 0.0  # (t0+2 and t0+5.1 are active)


def test_sliding_window_request_larger_than_capacity():
    config = RateLimitConfig(capacity=5, window_seconds=10.0)
    limiter = SlidingWindowStrategy(config)

    res = limiter.acquire(tokens=6, current_time=100.0)
    assert res.allowed is False
    assert res.retry_after_seconds == float("inf")


def test_sliding_window_invalid_tokens():
    config = RateLimitConfig(capacity=5, window_seconds=10.0)
    limiter = SlidingWindowStrategy(config)
    with pytest.raises(ValueError):
        limiter.acquire(tokens=0)
    with pytest.raises(ValueError):
        limiter.acquire(tokens=-1)
