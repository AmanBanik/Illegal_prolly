"""Deterministic hashing and percentage rollout stability tests."""

import pytest

from Proj_06.src.evaluator import compute_deterministic_bucket
from Proj_06.src.models import (
    EvaluationReason,
    RolloutConfig,
    RolloutVariant,
    UserContext,
    Variant,
)
from Proj_06.src.service import FeatureFlagService


def test_hashing_determinism_and_reproducibility() -> None:
    """Verify that hash bucketing is 100% deterministic and reproducible."""
    flag_key = "search_ranking_v2"
    user_id = "user_alpha_9876"

    bucket_1 = compute_deterministic_bucket(flag_key, user_id)
    bucket_2 = compute_deterministic_bucket(flag_key, user_id)
    assert bucket_1 == bucket_2
    assert 0.0 <= bucket_1 < 100.0

    # Repeating across 50 iterations
    for _ in range(50):
        assert compute_deterministic_bucket(flag_key, user_id) == bucket_1


def test_monotonic_rollout_stability(service: FeatureFlagService) -> None:
    """CRITICAL TEST: Ensure users maintain their assigned variant as rollout ramps up.

    When ramping rollout percentage:
    10% -> 25% -> 50% -> 100%
    Any user assigned 'treatment' at 10% must remain in 'treatment' across all subsequent increases.
    """
    flag_key = "stream_compression_flag"
    service.create_flag(
        key=flag_key,
        name="Stream Compression Experiment",
        variants=[Variant("treatment"), Variant("control")],
        default_variant="control",
        rollout=RolloutConfig(
            variants=[RolloutVariant("treatment", 10.0), RolloutVariant("control", 90.0)]
        ),
    )

    num_users = 250
    users = [f"user_{i:04d}" for i in range(num_users)]

    # Phase 1: 10% Rollout
    treatment_10 = set()
    for uid in users:
        res = service.evaluate(flag_key, UserContext(user_id=uid))
        assert res.reason == EvaluationReason.PERCENTAGE_ROLLOUT
        if res.variant_key == "treatment":
            treatment_10.add(uid)

    assert len(treatment_10) > 0  # Some users should be bucketed into treatment

    # Phase 2: Ramp up to 25% Rollout
    service.update_flag(
        flag_key,
        rollout=RolloutConfig(
            variants=[RolloutVariant("treatment", 25.0), RolloutVariant("control", 75.0)]
        ),
    )

    treatment_25 = set()
    for uid in users:
        res = service.evaluate(flag_key, UserContext(user_id=uid))
        if res.variant_key == "treatment":
            treatment_25.add(uid)

    # Monotonicity check: All users from 10% MUST still be in 25%
    assert treatment_10.issubset(treatment_25)
    assert len(treatment_25) > len(treatment_10)

    # Phase 3: Ramp up to 50% Rollout
    service.update_flag(
        flag_key,
        rollout=RolloutConfig(
            variants=[RolloutVariant("treatment", 50.0), RolloutVariant("control", 50.0)]
        ),
    )

    treatment_50 = set()
    for uid in users:
        res = service.evaluate(flag_key, UserContext(user_id=uid))
        if res.variant_key == "treatment":
            treatment_50.add(uid)

    # Monotonicity check: All users from 25% MUST still be in 50%
    assert treatment_25.issubset(treatment_50)
    assert len(treatment_50) > len(treatment_25)

    # Phase 4: Ramp up to 100% Rollout
    service.update_flag(
        flag_key,
        rollout=RolloutConfig(
            variants=[RolloutVariant("treatment", 100.0), RolloutVariant("control", 0.0)]
        ),
    )

    for uid in users:
        res = service.evaluate(flag_key, UserContext(user_id=uid))
        assert res.variant_key == "treatment"


def test_multi_variant_percentage_rollout(service: FeatureFlagService) -> None:
    """Verify multi-variant cumulative bucketing across 3 variants."""
    flag_key = "button_color_experiment"
    service.create_flag(
        key=flag_key,
        name="Button Color A/B/C Test",
        variants=[Variant("blue"), Variant("green"), Variant("red")],
        default_variant="red",
        rollout=RolloutConfig(
            variants=[
                RolloutVariant("blue", 30.0),   # [0.0, 30.0)
                RolloutVariant("green", 20.0),  # [30.0, 50.0)
                RolloutVariant("red", 50.0),    # [50.0, 100.0)
            ]
        ),
    )

    counts = {"blue": 0, "green": 0, "red": 0}
    for i in range(500):
        uid = f"user_color_{i}"
        bucket = compute_deterministic_bucket(flag_key, uid)
        res = service.evaluate(flag_key, UserContext(user_id=uid))

        # Check exact bucket bounds
        if bucket < 30.0:
            assert res.variant_key == "blue"
        elif bucket < 50.0:
            assert res.variant_key == "green"
        else:
            assert res.variant_key == "red"

        counts[res.variant_key] += 1

    # Verify all variants received assignments roughly proportional to weights
    assert counts["blue"] > 0
    assert counts["green"] > 0
    assert counts["red"] > 0
    assert counts["red"] > counts["green"]  # 50% > 20%


def test_uniform_hash_distribution() -> None:
    """Verify hash bucket values distribute across the 0-100 spectrum."""
    buckets = [compute_deterministic_bucket("test_flag", f"user_{i}") for i in range(1000)]
    assert min(buckets) < 5.0
    assert max(buckets) > 95.0

    # In a 50/50 split, count should be between 43% and 57%
    below_50 = sum(1 for b in buckets if b < 50.0)
    assert 430 <= below_50 <= 570
