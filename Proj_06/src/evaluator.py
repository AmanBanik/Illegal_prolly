"""Rule evaluation engine and deterministic percentage-based bucketing."""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Dict, Optional, Tuple

from .models import (
    EvaluationReason,
    EvaluationResult,
    FeatureFlag,
    Operator,
    RolloutConfig,
    RuleCondition,
    TargetingRule,
    UserContext,
)


def compute_deterministic_bucket(flag_key: str, user_id: str) -> float:
    """Compute a deterministic hash bucket in the range [0.00, 100.00).

    Uses SHA-256 for uniform, cross-process, and multi-instance distribution
    stability, avoiding Python's process-seeded built-in hash().
    """
    key = f"{flag_key}:{user_id}".encode("utf-8")
    digest = hashlib.sha256(key).hexdigest()
    # Take first 8 hexadecimal characters (32 bits)
    hash_val = int(digest[:8], 16)
    # Scale to 0.00 - 99.99 with two decimal places
    return (hash_val % 10000) / 100.0


def evaluate_condition(condition: RuleCondition, attributes: Dict[str, Any]) -> bool:
    """Evaluate a single rule condition against the user attributes."""
    attr_name = condition.attribute
    op = condition.operator
    expected = condition.value

    # Check attribute presence
    if attr_name not in attributes:
        if op == Operator.NOT_EQUALS:
            return expected is not None
        if op == Operator.NOT_IN:
            return True
        return False

    actual = attributes[attr_name]

    try:
        if op == Operator.EQUALS:
            # Strict boolean trap avoidance: True != 1
            if isinstance(actual, bool) != isinstance(expected, bool):
                return False
            return actual == expected

        if op == Operator.NOT_EQUALS:
            if isinstance(actual, bool) != isinstance(expected, bool):
                return True
            return actual != expected

        if op == Operator.IN:
            if not isinstance(expected, (list, tuple, set)):
                return False
            # Check equality with boolean type safety
            for item in expected:
                if (
                    isinstance(actual, bool) == isinstance(item, bool)
                    and actual == item
                ):
                    return True
            return False

        if op == Operator.NOT_IN:
            if not isinstance(expected, (list, tuple, set)):
                return False
            for item in expected:
                if (
                    isinstance(actual, bool) == isinstance(item, bool)
                    and actual == item
                ):
                    return False
            return True

        if op == Operator.CONTAINS:
            if isinstance(actual, str) and isinstance(expected, str):
                return expected in actual
            if isinstance(actual, (list, tuple, set)):
                for item in actual:
                    if (
                        isinstance(item, bool) == isinstance(expected, bool)
                        and item == expected
                    ):
                        return True
            return False

        if op == Operator.STARTS_WITH:
            if isinstance(actual, str) and isinstance(expected, str):
                return actual.startswith(expected)
            return False

        if op == Operator.ENDS_WITH:
            if isinstance(actual, str) and isinstance(expected, str):
                return actual.endswith(expected)
            return False

        # Numeric comparisons: strictly reject boolean inputs
        if op in (
            Operator.GREATER_THAN,
            Operator.GREATER_THAN_OR_EQUAL,
            Operator.LESS_THAN,
            Operator.LESS_THAN_OR_EQUAL,
        ):
            if isinstance(actual, bool) or isinstance(expected, bool):
                return False
            actual_num = float(actual)
            expected_num = float(expected)

            if op == Operator.GREATER_THAN:
                return actual_num > expected_num
            if op == Operator.GREATER_THAN_OR_EQUAL:
                return actual_num >= expected_num
            if op == Operator.LESS_THAN:
                return actual_num < expected_num
            if op == Operator.LESS_THAN_OR_EQUAL:
                return actual_num <= expected_num

    except (ValueError, TypeError):
        return False

    return False


def evaluate_rule(rule: TargetingRule, attributes: Dict[str, Any]) -> bool:
    """Evaluate all conditions in a rule with AND semantics."""
    if not rule.conditions:
        return False
    return all(evaluate_condition(c, attributes) for c in rule.conditions)


def resolve_rollout(
    rollout: RolloutConfig, flag_key: str, user_id: str
) -> Tuple[str, float]:
    """Resolve variant from a percentage rollout with monotonic stability."""
    bucket = compute_deterministic_bucket(flag_key, user_id)
    cumulative = 0.0

    for item in rollout.variants:
        cumulative += item.weight
        if bucket < cumulative:
            return item.variant_key, bucket

    # Fallback to last variant if floating point precision edge
    return rollout.variants[-1].variant_key, bucket


def evaluate_flag(flag: FeatureFlag, context: UserContext) -> EvaluationResult:
    """Evaluate a feature flag against user context.

    Follows strict precedence:
    1. If flag is disabled -> returns default_variant with DISABLED reason.
    2. Ordered targeting rules -> first match wins with RULE_MATCH reason.
    3. Deterministic percentage rollout -> returns assigned variant with PERCENTAGE_ROLLOUT reason.
    4. Default fallback -> returns default_variant with DEFAULT_FALLBACK reason.
    """
    variant_map = {v.key: copy.deepcopy(v.attachment) for v in flag.variants}

    # 1. Disabled Check
    if not flag.enabled:
        return EvaluationResult(
            flag_key=flag.key,
            enabled=False,
            variant_key=flag.default_variant,
            attachment=variant_map.get(flag.default_variant),
            reason=EvaluationReason.DISABLED,
        )

    # 2. Ordered Rule Evaluation (first-match-wins)
    for rule in flag.rules:
        if evaluate_rule(rule, context.attributes):
            return EvaluationResult(
                flag_key=flag.key,
                enabled=True,
                variant_key=rule.variant_key,
                attachment=variant_map.get(rule.variant_key),
                reason=EvaluationReason.RULE_MATCH,
                rule_id=rule.id,
            )

    # 3. Deterministic Percentage Rollout
    if flag.rollout and flag.rollout.variants:
        assigned_variant, bucket = resolve_rollout(flag.rollout, flag.key, context.user_id)
        return EvaluationResult(
            flag_key=flag.key,
            enabled=True,
            variant_key=assigned_variant,
            attachment=variant_map.get(assigned_variant),
            reason=EvaluationReason.PERCENTAGE_ROLLOUT,
            bucket_value=bucket,
        )

    # 4. Fallback Default
    return EvaluationResult(
        flag_key=flag.key,
        enabled=True,
        variant_key=flag.default_variant,
        attachment=variant_map.get(flag.default_variant),
        reason=EvaluationReason.DEFAULT_FALLBACK,
    )
