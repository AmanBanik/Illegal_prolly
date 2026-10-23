"""CRUD operations and specification validation tests for FeatureFlagService."""

import pytest

from Proj_06.src.exceptions import (
    FlagAlreadyExistsError,
    FlagNotFoundError,
    InvalidVariantError,
    ValidationError,
)
from Proj_06.src.models import (
    Operator,
    RolloutConfig,
    RolloutVariant,
    RuleCondition,
    TargetingRule,
    Variant,
)
from Proj_06.src.service import FeatureFlagService


def test_create_and_get_flag_success(service: FeatureFlagService) -> None:
    """Verify basic flag creation and retrieval."""
    flag = service.create_flag(
        key="dark_mode",
        name="Dark Mode Toggle",
        description="Enables dark UI palette",
        enabled=True,
        variants=[Variant(key="off"), Variant(key="on", attachment={"hex": "#000"})],
        default_variant="off",
    )
    assert flag.key == "dark_mode"
    assert flag.name == "Dark Mode Toggle"
    assert flag.enabled is True
    assert len(flag.variants) == 2
    assert flag.default_variant == "off"

    retrieved = service.get_flag("dark_mode")
    assert retrieved.key == flag.key
    assert retrieved.default_variant == "off"


def test_create_duplicate_flag_raises_conflict(service: FeatureFlagService) -> None:
    """Verify attempting to create a flag with existing key raises FlagAlreadyExistsError."""
    service.create_flag(
        key="beta_feature",
        name="Beta",
        variants=[Variant(key="v1")],
        default_variant="v1",
    )
    with pytest.raises(FlagAlreadyExistsError) as exc:
        service.create_flag(
            key="beta_feature",
            name="Beta Duplicate",
            variants=[Variant(key="v1")],
            default_variant="v1",
        )
    assert "already exists" in str(exc.value)


def test_invalid_variant_references(service: FeatureFlagService) -> None:
    """Verify default_variant, rule variant_key, and rollout variants must exist in variants."""
    # Unknown default variant
    with pytest.raises(InvalidVariantError) as exc:
        service.create_flag(
            key="test_flag",
            name="Test",
            variants=[Variant(key="v1"), Variant(key="v2")],
            default_variant="unknown_v3",
        )
    assert "default_variant 'unknown_v3' must exist" in str(exc.value)

    # Unknown rule variant
    with pytest.raises(InvalidVariantError) as exc2:
        service.create_flag(
            key="test_flag",
            name="Test",
            variants=[Variant(key="v1")],
            default_variant="v1",
            rules=[
                TargetingRule(
                    id="r1",
                    variant_key="non_existent",
                    conditions=[RuleCondition("country", Operator.EQUALS, "US")],
                )
            ],
        )
    assert "references unknown variant 'non_existent'" in str(exc2.value)

    # Unknown rollout variant
    with pytest.raises(InvalidVariantError) as exc3:
        service.create_flag(
            key="test_flag",
            name="Test",
            variants=[Variant(key="v1")],
            default_variant="v1",
            rollout=RolloutConfig(variants=[RolloutVariant("ghost", 100.0)]),
        )
    assert "Rollout references unknown variant 'ghost'" in str(exc3.value)


def test_validation_errors_on_creation(service: FeatureFlagService) -> None:
    """Verify input validation rejects invalid keys, empty variants, and bad weights."""
    # Invalid characters in key
    with pytest.raises(ValidationError):
        service.create_flag("flag with spaces", "Name", [Variant("on")], "on")

    # Empty variants
    with pytest.raises(ValidationError):
        service.create_flag("empty_variants", "Name", [], "on")

    # Duplicate variant keys
    with pytest.raises(ValidationError) as exc:
        service.create_flag("dup_variants", "Name", [Variant("v1"), Variant("v1")], "v1")
    assert "Duplicate variant key" in str(exc.value)

    # Rollout weights not summing to 100
    with pytest.raises(ValidationError) as exc:
        service.create_flag(
            key="bad_weights",
            name="Weights",
            variants=[Variant("a"), Variant("b")],
            default_variant="a",
            rollout=RolloutConfig(
                variants=[RolloutVariant("a", 30.0), RolloutVariant("b", 40.0)]
            ),
        )
    assert "Rollout weights must sum to exactly 100.0" in str(exc.value)

    # Negative rollout weight
    with pytest.raises(ValidationError):
        service.create_flag(
            key="neg_weights",
            name="Weights",
            variants=[Variant("a"), Variant("b")],
            default_variant="a",
            rollout=RolloutConfig(
                variants=[RolloutVariant("a", -10.0), RolloutVariant("b", 110.0)]
            ),
        )


def test_update_flag_success_and_errors(service: FeatureFlagService) -> None:
    """Verify updating flag properties and rules atomically."""
    service.create_flag(
        key="banner_alert",
        name="Banner Alert",
        variants=[Variant("off"), Variant("on")],
        default_variant="off",
        enabled=False,
    )

    # Update enabled status and description
    updated = service.update_flag("banner_alert", enabled=True, description="Updated desc")
    assert updated.enabled is True
    assert updated.description == "Updated desc"

    # Non-existent flag update raises FlagNotFoundError
    with pytest.raises(FlagNotFoundError):
        service.update_flag("non_existent", enabled=True)

    # Invalid update with bad default variant
    with pytest.raises(InvalidVariantError):
        service.update_flag("banner_alert", default_variant="invalid_variant")


def test_delete_and_list_flags(service: FeatureFlagService) -> None:
    """Verify deleting a flag and listing all registered flags."""
    service.create_flag("f1", "Flag 1", [Variant("a")], "a")
    service.create_flag("f2", "Flag 2", [Variant("b")], "b")

    flags = service.list_flags()
    assert len(flags) == 2
    keys = {f.key for f in flags}
    assert keys == {"f1", "f2"}

    # Delete f1
    assert service.delete_flag("f1") is True
    with pytest.raises(FlagNotFoundError):
        service.get_flag("f1")

    assert len(service.list_flags()) == 1

    # Delete non-existent flag
    with pytest.raises(FlagNotFoundError):
        service.delete_flag("f1")


def test_service_stats_and_clear(service: FeatureFlagService) -> None:
    """Verify aggregate metric reporting and state clearing."""
    assert service.get_stats() == {
        "total_flags": 0,
        "active_flags": 0,
        "inactive_flags": 0,
        "total_rules": 0,
    }

    service.create_flag("f1", "Flag 1", [Variant("a")], "a", enabled=True)
    service.create_flag("f2", "Flag 2", [Variant("b")], "b", enabled=False)

    stats = service.get_stats()
    assert stats["total_flags"] == 2
    assert stats["active_flags"] == 1
    assert stats["inactive_flags"] == 1

    service.clear()
    assert service.get_stats()["total_flags"] == 0
