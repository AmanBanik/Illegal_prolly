import copy
import threading
from typing import Dict, Optional, Tuple
from .models import RateLimitConfig, RateLimitResult, RateLimiterStats, StrategyType
from .strategies import RateLimitStrategy, SlidingWindowStrategy, TokenBucketStrategy


class RateLimiter:
    """Production-grade In-Memory Rate Limiter for API Gateways.

    Supports:
    - Multi-tenant isolation: independent state per (client_id, resource).
    - Pluggable strategies: Sliding Window and Token Bucket.
    - Hierarchical rules: default rules with per-client or per-resource overrides.
    - Thread-safe statistics tracking and concurrent request handling.
    - Defensive copying of state snapshots.
    """

    def __init__(
        self,
        default_config: Optional[RateLimitConfig] = None,
        default_strategy: StrategyType = StrategyType.SLIDING_WINDOW,
    ):
        self._default_config = default_config or RateLimitConfig(capacity=100, window_seconds=60.0)
        self._default_strategy = default_strategy

        # Specific rules: (client_id, resource) or (client_id, None) or (None, resource)
        self._rules: Dict[Tuple[Optional[str], Optional[str]], Tuple[RateLimitConfig, StrategyType]] = {}

        # Active strategy instances: (client_id, resource) -> RateLimitStrategy
        self._instances: Dict[Tuple[str, str], RateLimitStrategy] = {}

        # Statistics: (client_id, resource) -> RateLimiterStats
        self._stats: Dict[Tuple[str, str], RateLimiterStats] = {}
        self._global_stats = RateLimiterStats()

        # Master lock for dictionary modifications
        self._master_lock = threading.Lock()

    def configure_rule(
        self,
        client_id: Optional[str] = None,
        resource: Optional[str] = None,
        config: Optional[RateLimitConfig] = None,
        strategy: Optional[StrategyType] = None,
    ) -> None:
        """Register a custom rate limit rule for a client, resource, or pair."""
        if config is None:
            config = self._default_config
        if strategy is None:
            strategy = self._default_strategy

        key = (client_id, resource)
        with self._master_lock:
            self._rules[key] = (config, strategy)
            # Invalidate any cached instance for this key to reload config
            if client_id is not None and resource is not None:
                self._instances.pop((client_id, resource), None)

    def _resolve_config_and_strategy(
        self, client_id: str, resource: str
    ) -> Tuple[RateLimitConfig, StrategyType]:
        """Resolves configuration with precedence:
        1. Exact (client_id, resource)
        2. Client specific (client_id, None)
        3. Resource specific (None, resource)
        4. Global default
        """
        # Note: caller holds master_lock or reads immutable references
        if (client_id, resource) in self._rules:
            return self._rules[(client_id, resource)]
        if (client_id, None) in self._rules:
            return self._rules[(client_id, None)]
        if (None, resource) in self._rules:
            return self._rules[(None, resource)]
        return self._default_config, self._default_strategy

    def _get_or_create_instance(self, client_id: str, resource: str) -> RateLimitStrategy:
        key = (client_id, resource)
        with self._master_lock:
            if key not in self._instances:
                cfg, strat_type = self._resolve_config_and_strategy(client_id, resource)
                if strat_type == StrategyType.SLIDING_WINDOW:
                    self._instances[key] = SlidingWindowStrategy(cfg)
                elif strat_type == StrategyType.TOKEN_BUCKET:
                    self._instances[key] = TokenBucketStrategy(cfg)
                else:
                    raise ValueError(f"Unknown strategy: {strat_type}")

                if key not in self._stats:
                    self._stats[key] = RateLimiterStats()

            return self._instances[key]

    def allow_request(
        self,
        client_id: str,
        resource: str,
        tokens: int = 1,
        current_time: Optional[float] = None,
    ) -> RateLimitResult:
        """Evaluate whether a request from client_id for resource should be admitted."""
        if not client_id or not isinstance(client_id, str):
            raise ValueError("client_id must be a non-empty string")
        if not resource or not isinstance(resource, str):
            raise ValueError("resource must be a non-empty string")
        if tokens <= 0:
            raise ValueError(f"tokens must be positive integer, got {tokens}")

        instance = self._get_or_create_instance(client_id, resource)
        result = instance.acquire(tokens=tokens, current_time=current_time)

        # Update stats
        key = (client_id, resource)
        with self._master_lock:
            stats = self._stats[key]
            stats.total_requests += 1
            self._global_stats.total_requests += 1

            if result.allowed:
                stats.allowed_requests += 1
                self._global_stats.allowed_requests += 1
            else:
                stats.rejected_requests += 1
                self._global_stats.rejected_requests += 1

        return result

    def get_stats(
        self, client_id: Optional[str] = None, resource: Optional[str] = None
    ) -> RateLimiterStats:
        """Retrieve defensive copy of statistics."""
        with self._master_lock:
            if client_id is None and resource is None:
                return copy.deepcopy(self._global_stats)

            if client_id is not None and resource is not None:
                key = (client_id, resource)
                stats = self._stats.get(key, RateLimiterStats())
                return copy.deepcopy(stats)

            # Aggregate over matching keys
            agg = RateLimiterStats()
            for (c, r), s in self._stats.items():
                if (client_id is None or c == client_id) and (resource is None or r == resource):
                    agg.total_requests += s.total_requests
                    agg.allowed_requests += s.allowed_requests
                    agg.rejected_requests += s.rejected_requests
            return agg

    def reset(self) -> None:
        """Clear all active limits and reset statistics."""
        with self._master_lock:
            self._instances.clear()
            self._stats.clear()
            self._global_stats = RateLimiterStats()
