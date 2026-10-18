import concurrent.futures
from src.limiter import RateLimiter
from src.models import RateLimitConfig, StrategyType


def test_concurrent_sliding_window_exact_capacity():
    """Verify that under heavy concurrent load, exactly `capacity` requests are admitted."""
    capacity = 25
    total_workers = 100

    limiter = RateLimiter(
        default_config=RateLimitConfig(capacity=capacity, window_seconds=60.0),
        default_strategy=StrategyType.SLIDING_WINDOW,
    )

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [
            executor.submit(limiter.allow_request, "tenant_concurrent", "/generate", 1, 1000.0)
            for _ in range(total_workers)
        ]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    allowed_count = sum(1 for r in results if r.allowed)
    rejected_count = sum(1 for r in results if not r.allowed)

    assert allowed_count == capacity
    assert rejected_count == total_workers - capacity

    stats = limiter.get_stats("tenant_concurrent", "/generate")
    assert stats.total_requests == total_workers
    assert stats.allowed_requests == capacity
    assert stats.rejected_requests == total_workers - capacity


def test_concurrent_multi_tenant_isolation():
    """Ensure multiple tenants operating concurrently do not interfere with each other."""
    num_tenants = 10
    requests_per_tenant = 20
    capacity_per_tenant = 5

    limiter = RateLimiter(
        default_config=RateLimitConfig(capacity=capacity_per_tenant, window_seconds=60.0),
        default_strategy=StrategyType.TOKEN_BUCKET,
    )

    def worker(tenant_id: int):
        allowed = 0
        for _ in range(requests_per_tenant):
            res = limiter.allow_request(f"client_{tenant_id}", "/resource", 1, 500.0)
            if res.allowed:
                allowed += 1
        return tenant_id, allowed

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_tenants) as executor:
        futures = [executor.submit(worker, i) for i in range(num_tenants)]
        for f in concurrent.futures.as_completed(futures):
            tid, allowed = f.result()
            assert allowed == capacity_per_tenant, f"Tenant {tid} got {allowed} allowed instead of {capacity_per_tenant}"

    global_stats = limiter.get_stats()
    assert global_stats.total_requests == num_tenants * requests_per_tenant
    assert global_stats.allowed_requests == num_tenants * capacity_per_tenant
    assert global_stats.rejected_requests == (num_tenants * requests_per_tenant) - (num_tenants * capacity_per_tenant)
