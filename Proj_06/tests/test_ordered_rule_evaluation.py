"""Ordered targeting rule evaluation and multi-condition AND semantics tests."""

import pytest

from Proj_06.src.models import (
    EvaluationReason,
    Operator,
    RuleCondition,
    TargetingRule,
    UserContext,
    Variant,
)
from Proj_06.src.service import FeatureFlagService


def test_first_match_wins_ordering(service: FeatureFlagService) -> None:
    """Verify that targeting rules evaluate in strict order: first match wins."""
    service.create_flag(
        key="pricing_tier",
        name="Pricing Tier Test",
        variants=[Variant("default_price"), Variant("us_price"), Variant("gold_price")],
        default_variant="default_price",
        rules=[
            TargetingRule(
                id="rule_us",
                variant_key="us_price",
                conditions=[RuleCondition("country", Operator.EQUALS, "US")],
            ),
            TargetingRule(
                id="rule_gold",
                variant_key="gold_price",
                conditions=[RuleCondition("tier", Operator.EQUALS, "gold")],
            ),
        ],
    )

    # User matches both rule_us and rule_gold
    user_both = UserContext(user_id="user_1", attributes={"country": "US", "tier": "gold"})
    res = service.evaluate("pricing_tier", user_both)
    assert res.variant_key == "us_price"
    assert res.reason == EvaluationReason.RULE_MATCH
    assert res.rule_id == "rule_us"

    # User matches only rule_gold
    user_gold = UserContext(user_id="user_2", attributes={"country": "UK", "tier": "gold"})
    res_gold = service.evaluate("pricing_tier", user_gold)
    assert res_gold.variant_key == "gold_price"
    assert res_gold.rule_id == "rule_gold"


def test_and_condition_evaluation(service: FeatureFlagService) -> None:
    """Verify all conditions within a rule must be satisfied (AND logic)."""
    service.create_flag(
        key="vip_perk",
        name="VIP Perk",
        variants=[Variant("standard"), Variant("premium")],
        default_variant="standard",
        rules=[
            TargetingRule(
                id="strict_vip",
                variant_key="premium",
                conditions=[
                    RuleCondition("is_vip", Operator.EQUALS, True),
                    RuleCondition("loyalty_years", Operator.GREATER_THAN_OR_EQUAL, 3),
                    RuleCondition("account_standing", Operator.EQUALS, "good"),
                ],
            )
        ],
    )

    # Matches only 2 out of 3 -> fails rule
    partial_user = UserContext(
        user_id="u_partial",
        attributes={"is_vip": True, "loyalty_years": 5, "account_standing": "probation"},
    )
    res_partial = service.evaluate("vip_perk", partial_user)
    assert res_partial.variant_key == "standard"
    assert res_partial.reason == EvaluationReason.DEFAULT_FALLBACK

    # Matches all 3 -> triggers rule
    full_user = UserContext(
        user_id="u_full",
        attributes={"is_vip": True, "loyalty_years": 4, "account_standing": "good"},
    )
    res_full = service.evaluate("vip_perk", full_user)
    assert res_full.variant_key == "premium"
    assert res_full.reason == EvaluationReason.RULE_MATCH
    assert res_full.rule_id == "strict_vip"


def test_disabled_flag_bypasses_all_rules(service: FeatureFlagService) -> None:
    """Verify disabled flags immediately return default_variant with DISABLED reason."""
    service.create_flag(
        key="killswitch_flag",
        name="Killswitch",
        enabled=False,
        variants=[Variant("off"), Variant("vip_on")],
        default_variant="off",
        rules=[
            TargetingRule(
                id="vip_rule",
                variant_key="vip_on",
                conditions=[RuleCondition("is_admin", Operator.EQUALS, True)],
            )
        ],
    )

    admin_user = UserContext(user_id="admin_1", attributes={"is_admin": True})
    res = service.evaluate("killswitch_flag", admin_user)
    assert res.enabled is False
    assert res.variant_key == "off"
    assert res.reason == EvaluationReason.DISABLED
    assert res.rule_id is None


def test_evaluate_all_flags(service: FeatureFlagService, sample_checkout_flag) -> None:
    """Verify evaluate_all evaluates every registered flag for a user context."""
    service.create_flag(
        key="nav_bar",
        name="Nav Bar",
        variants=[Variant("v1"), Variant("v2")],
        default_variant="v1",
    )

    context = UserContext(user_id="user_test", attributes={"is_vip": True, "tier": "gold"})
    results = service.evaluate_all(context)

    assert len(results) == 2
    assert "new_checkout_flow" in results
    assert "nav_bar" in results
    assert results["new_checkout_flow"].variant_key == "express"
    assert results["nav_bar"].variant_key == "v1"
