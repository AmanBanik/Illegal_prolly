"""Defensive copy snapshot and state immutability tests for FeatureFlagService."""

import pytest

from Proj_06.src.models import (
    Operator,
    RuleCondition,
    TargetingRule,
    UserContext,
    Variant,
)
from Proj_06.src.service import FeatureFlagService


def test_flag_retrieval_defensive_copy(service: FeatureFlagService) -> None:
    """Ensure mutating properties on a retrieved FeatureFlag has zero effect on service state."""
    service.create_flag(
        key="mutable_test_flag",
        name="Original Name",
        description="Original Desc",
        variants=[Variant("v1"), Variant("v2")],
        default_variant="v1",
        rules=[
            TargetingRule("r1", [RuleCondition("country", Operator.EQUALS, "US")], "v2")
        ],
    )

    flag = service.get_flag("mutable_test_flag")
    assert flag.name == "Original Name"

    # Malicious mutation
    flag.name = "Defaced Name"
    flag.variants.clear()
    flag.rules.clear()

    # Verify underlying store is untouched
    pristine = service.get_flag("mutable_test_flag")
    assert pristine.name == "Original Name"
    assert len(pristine.variants) == 2
    assert len(pristine.rules) == 1


def test_evaluation_attachment_defensive_copy(service: FeatureFlagService) -> None:
    """Ensure mutating an evaluation result's attachment payload does not corrupt stored metadata."""
    service.create_flag(
        key="rich_payload_flag",
        name="Payload Flag",
        variants=[
            Variant(key="control", attachment={"timeout_ms": 500, "features": ["cache"]}),
            Variant(key="treatment", attachment={"timeout_ms": 100, "features": ["cache", "ai"]}),
        ],
        default_variant="control",
    )

    user = UserContext(user_id="user_attach_1")
    res1 = service.evaluate("rich_payload_flag", user)
    assert res1.attachment == {"timeout_ms": 500, "features": ["cache"]}

    # Mutate the attachment dictionary in-place
    res1.attachment["timeout_ms"] = 99999
    res1.attachment["features"].clear()

    # Re-evaluate for next caller
    res2 = service.evaluate("rich_payload_flag", user)
    assert res2.attachment["timeout_ms"] == 500
    assert res2.attachment["features"] == ["cache"]


def test_list_flags_defensive_copy(service: FeatureFlagService) -> None:
    """Ensure mutating the list returned by list_flags does not affect service storage."""
    service.create_flag("f1", "Flag 1", [Variant("a")], "a")
    service.create_flag("f2", "Flag 2", [Variant("b")], "b")

    flags = service.list_flags()
    assert len(flags) == 2

    # Clear external list
    flags.clear()

    assert len(service.list_flags()) == 2


def test_flag_creation_input_defensive_copy(service: FeatureFlagService) -> None:
    """Ensure mutating input lists after calling create_flag does not corrupt stored flag."""
    input_variants = [Variant("a"), Variant("b")]
    input_rules = [TargetingRule("r1", [RuleCondition("attr", Operator.EQUALS, "val")], "b")]

    service.create_flag(
        key="input_iso_flag",
        name="Input Isolation",
        variants=input_variants,
        default_variant="a",
        rules=input_rules,
    )

    # Mutate caller input lists
    input_variants.append(Variant("c"))
    input_rules.clear()

    stored = service.get_flag("input_iso_flag")
    assert len(stored.variants) == 2
    assert len(stored.rules) == 1
