import pytest
from Proj_01.src.models import RateLimitConfig
from Proj_01.src.strategies.token_bucket import TokenBucketStrategy


def test_token_bucket_burst_and_refill():
    # Capacity 10, refills at 2 tokens/sec
    config = RateLimitConfig(capacity=10, window_seconds=5.0, refill_rate=2.0)
    limiter = TokenBucketStrategy(config)

    t0 = 500.0
    # Burst 8 tokens
    r1 = limiter.acquire(tokens=8, current_time=t0)
    assert r1.allowed is True
    assert pytest.approx(r1.remaining_capacity, 0.01) == 2.0

    # Try 5 tokens -> fails because only 2 left
    r2 = limiter.acquire(tokens=5, current_time=t0)
    assert r2.allowed is False
    assert pytest.approx(r2.remaining_capacity, 0.01) == 2.0
    # Needs 3 more tokens at 2 tokens/sec -> 1.5 seconds
    assert pytest.approx(r2.retry_after_seconds, 0.01) == 1.5

    # Advance 2 seconds -> should refill 4 tokens -> total 6 tokens
    r3 = limiter.acquire(tokens=5, current_time=t0 + 2.0)
    assert r3.allowed is True
    assert pytest.approx(r3.remaining_capacity, 0.01) == 1.0


def test_token_bucket_cap_at_capacity():
    config = RateLimitConfig(capacity=5, window_seconds=5.0, refill_rate=1.0)
    limiter = TokenBucketStrategy(config)

    t0 = 1000.0
    # Advance time by 100 seconds without requests -> tokens should not exceed capacity of 5
    res = limiter.acquire(tokens=5, current_time=t0 + 100.0)
    assert res.allowed is True
    assert pytest.approx(res.remaining_capacity, 0.01) == 0.0


def test_token_bucket_oversized_request():
    config = RateLimitConfig(capacity=5, window_seconds=5.0)
    limiter = TokenBucketStrategy(config)
    res = limiter.acquire(tokens=10, current_time=100.0)
    assert res.allowed is False
    assert res.retry_after_seconds == float("inf")
