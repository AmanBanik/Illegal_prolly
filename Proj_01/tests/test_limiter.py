import pytest
from Proj_01.src.limiter import RateLimiter
from Proj_01.src.models import RateLimitConfig, StrategyType


def test_rate_limiter_tenant_and_resource_isolation():
    limiter = RateLimiter(
        default_config=RateLimitConfig(capacity=2, window_seconds=10.0),
        default_strategy=StrategyType.SLIDING_WINDOW,
    )

    t0 = 100.0
    # Client A on /chat
    assert limiter.allow_request("client_a", "/chat", 1, t0).allowed is True
    assert limiter.allow_request("client_a", "/chat", 1, t0).allowed is True
    assert limiter.allow_request("client_a", "/chat", 1, t0).allowed is False

    # Client B on /chat should have independent capacity
    assert limiter.allow_request("client_b", "/chat", 1, t0).allowed is True

    # Client A on /embeddings should also have independent capacity
    assert limiter.allow_request("client_a", "/embeddings", 1, t0).allowed is True


def test_rate_limiter_statistics_tracking():
    limiter = RateLimiter(
        default_config=RateLimitConfig(capacity=1, window_seconds=10.0),
        default_strategy=StrategyType.SLIDING_WINDOW,
    )

    limiter.allow_request("client_x", "res_1", 1)
    limiter.allow_request("client_x", "res_1", 1)  # rejected
    limiter.allow_request("client_y", "res_1", 1)  # allowed

    stats_x = limiter.get_stats("client_x", "res_1")
    assert stats_x.total_requests == 2
    assert stats_x.allowed_requests == 1
    assert stats_x.rejected_requests == 1

    stats_global = limiter.get_stats()
    assert stats_global.total_requests == 3
    assert stats_global.allowed_requests == 2
    assert stats_global.rejected_requests == 1


def test_rate_limiter_defensive_copy():
    limiter = RateLimiter()
    limiter.allow_request("client_1", "/api")

    stats = limiter.get_stats("client_1", "/api")
    # Mutating returned object
    stats.total_requests = 99999

    stats_clean = limiter.get_stats("client_1", "/api")
    assert stats_clean.total_requests == 1
