"""Thread-safe Feature Flag & Experiment service with CRUD and evaluation logic."""

from __future__ import annotations

import copy
import re
import threading
import time
from typing import Any, Dict, List, Optional

from .evaluator import evaluate_flag
from .exceptions import (
    FlagAlreadyExistsError,
    FlagNotFoundError,
    InvalidVariantError,
    ValidationError,
)
from .models import (
    EvaluationResult,
    FeatureFlag,
    Operator,
    RolloutConfig,
    RolloutVariant,
    RuleCondition,
    TargetingRule,
    UserContext,
    Variant,
)


class FeatureFlagService:
    """Central service managing flag configurations and real-time evaluations."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._flags: Dict[str, FeatureFlag] = {}

    # -------------------------------------------------------------------------
    # Validation & Normalization Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _validate_non_empty_string(value: Any, field_name: str) -> str:
        """Validate that a field is a non-empty, non-whitespace string."""
        if isinstance(value, bool) or not isinstance(value, str):
            raise ValidationError(
                f"Field '{field_name}' must be a string, received {type(value).__name__}."
            )
        cleaned = value.strip()
        if not cleaned:
            raise ValidationError(f"Field '{field_name}' cannot be empty or whitespace-only.")
        return cleaned

    @staticmethod
    def _validate_flag_key(key: Any) -> str:
        """Ensure flag key conforms to valid identifier format."""
        cleaned = FeatureFlagService._validate_non_empty_string(key, "key")
        if not re.match(r"^[a-zA-Z0-9_\-\.]+$", cleaned):
            raise ValidationError(
                f"Flag key '{cleaned}' contains invalid characters. "
                "Only alphanumeric characters, underscores, hyphens, and dots are allowed."
            )
        return cleaned

    def _validate_flag_specification(
        self,
        key: str,
        name: str,
        variants: List[Variant],
        default_variant: str,
        rules: List[TargetingRule],
        rollout: Optional[RolloutConfig],
    ) -> None:
        """Enforce configuration validity, invariant consistency, and variant references."""
        if not variants:
            raise ValidationError("A feature flag must define at least one variant.")

        variant_keys = set()
        for v in variants:
            v_key = self._validate_non_empty_string(v.key, "variant.key")
            if v_key in variant_keys:
                raise ValidationError(f"Duplicate variant key detected: '{v_key}'.")
            variant_keys.add(v_key)

        if default_variant not in variant_keys:
            raise InvalidVariantError(
                f"default_variant '{default_variant}' must exist in defined variants: {sorted(variant_keys)}."
            )

        # Validate targeting rules
        for r in rules:
            self._validate_non_empty_string(r.id, "rule.id")
            if r.variant_key not in variant_keys:
                raise InvalidVariantError(
                    f"Rule '{r.id}' references unknown variant '{r.variant_key}'."
                )
            if not r.conditions:
                raise ValidationError(f"Rule '{r.id}' must specify at least one condition.")
            for c in r.conditions:
                self._validate_non_empty_string(c.attribute, "condition.attribute")
                if not isinstance(c.operator, Operator):
                    try:
                        c.operator = Operator(c.operator)
                    except ValueError:
                        raise ValidationError(f"Unsupported operator: '{c.operator}'.")

        # Validate rollout configuration
        if rollout is not None:
            if not rollout.variants:
                raise ValidationError("Rollout configuration cannot be empty.")
            total_weight = 0.0
            for rv in rollout.variants:
                if rv.variant_key not in variant_keys:
                    raise InvalidVariantError(
                        f"Rollout references unknown variant '{rv.variant_key}'."
                    )
                if isinstance(rv.weight, bool) or not isinstance(rv.weight, (int, float)):
                    raise ValidationError(f"Rollout weight for '{rv.variant_key}' must be numeric.")
                if rv.weight < 0.0:
                    raise ValidationError(f"Rollout weight for '{rv.variant_key}' cannot be negative.")
                total_weight += float(rv.weight)

            if abs(total_weight - 100.0) > 0.01:
                raise ValidationError(
                    f"Rollout weights must sum to exactly 100.0, received {total_weight:.2f}."
                )

    # -------------------------------------------------------------------------
    # CRUD Operations
    # -------------------------------------------------------------------------

    def create_flag(
        self,
        key: str,
        name: str,
        variants: List[Variant],
        default_variant: str,
        description: str = "",
        enabled: bool = True,
        rules: Optional[List[TargetingRule]] = None,
        rollout: Optional[RolloutConfig] = None,
    ) -> FeatureFlag:
        """Register a new feature flag configuration."""
        valid_key = self._validate_flag_key(key)
        valid_name = self._validate_non_empty_string(name, "name")
        rules_list = rules if rules is not None else []

        if not isinstance(enabled, bool):
            raise ValidationError(f"Field 'enabled' must be boolean, received {type(enabled).__name__}.")

        with self._lock:
            if valid_key in self._flags:
                raise FlagAlreadyExistsError(f"Feature flag with key '{valid_key}' already exists.")

            self._validate_flag_specification(
                key=valid_key,
                name=valid_name,
                variants=variants,
                default_variant=default_variant,
                rules=rules_list,
                rollout=rollout,
            )

            now = time.time()
            flag = FeatureFlag(
                key=valid_key,
                name=valid_name,
                description=str(description or "").strip(),
                enabled=enabled,
                variants=copy.deepcopy(variants),
                default_variant=default_variant,
                rules=copy.deepcopy(rules_list),
                rollout=copy.deepcopy(rollout),
                created_at=now,
                updated_at=now,
            )

            self._flags[valid_key] = flag
            return flag.copy()

    def get_flag(self, flag_key: str) -> FeatureFlag:
        """Retrieve a feature flag by key with snapshot isolation."""
        valid_key = self._validate_flag_key(flag_key)
        with self._lock:
            if valid_key not in self._flags:
                raise FlagNotFoundError(f"Feature flag '{valid_key}' not found.")
            return self._flags[valid_key].copy()

    def update_flag(
        self,
        flag_key: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        enabled: Optional[bool] = None,
        variants: Optional[List[Variant]] = None,
        default_variant: Optional[str] = None,
        rules: Optional[List[TargetingRule]] = None,
        rollout: Optional[RolloutConfig] = None,
    ) -> FeatureFlag:
        """Update existing flag configuration with atomic consistency."""
        valid_key = self._validate_flag_key(flag_key)

        with self._lock:
            if valid_key not in self._flags:
                raise FlagNotFoundError(f"Feature flag '{valid_key}' not found.")

            current = self._flags[valid_key]

            new_name = (
                self._validate_non_empty_string(name, "name") if name is not None else current.name
            )
            new_description = (
                str(description).strip() if description is not None else current.description
            )
            new_enabled = enabled if enabled is not None else current.enabled
            if not isinstance(new_enabled, bool):
                raise ValidationError("Field 'enabled' must be boolean.")

            new_variants = (
                copy.deepcopy(variants) if variants is not None else copy.deepcopy(current.variants)
            )
            new_default = (
                default_variant if default_variant is not None else current.default_variant
            )
            new_rules = copy.deepcopy(rules) if rules is not None else copy.deepcopy(current.rules)
            new_rollout = (
                copy.deepcopy(rollout) if rollout is not None else copy.deepcopy(current.rollout)
            )

            self._validate_flag_specification(
                key=valid_key,
                name=new_name,
                variants=new_variants,
                default_variant=new_default,
                rules=new_rules,
                rollout=new_rollout,
            )

            updated_flag = FeatureFlag(
                key=valid_key,
                name=new_name,
                description=new_description,
                enabled=new_enabled,
                variants=new_variants,
                default_variant=new_default,
                rules=new_rules,
                rollout=new_rollout,
                created_at=current.created_at,
                updated_at=time.time(),
            )

            self._flags[valid_key] = updated_flag
            return updated_flag.copy()

    def delete_flag(self, flag_key: str) -> bool:
        """Delete a feature flag from the service."""
        valid_key = self._validate_flag_key(flag_key)
        with self._lock:
            if valid_key not in self._flags:
                raise FlagNotFoundError(f"Feature flag '{valid_key}' not found.")
            del self._flags[valid_key]
            return True

    def list_flags(self) -> List[FeatureFlag]:
        """List all registered feature flags."""
        with self._lock:
            return [f.copy() for f in self._flags.values()]

    # -------------------------------------------------------------------------
    # Evaluation Engine
    # -------------------------------------------------------------------------

    def evaluate(self, flag_key: str, context: UserContext) -> EvaluationResult:
        """Evaluate a single flag for a user context."""
        valid_key = self._validate_flag_key(flag_key)
        if not isinstance(context, UserContext):
            raise ValidationError("Evaluation requires a valid UserContext instance.")

        with self._lock:
            if valid_key not in self._flags:
                raise FlagNotFoundError(f"Feature flag '{valid_key}' not found.")
            flag = self._flags[valid_key]
            return evaluate_flag(flag, context)

    def evaluate_all(self, context: UserContext) -> Dict[str, EvaluationResult]:
        """Evaluate all flags for the given user context."""
        if not isinstance(context, UserContext):
            raise ValidationError("Evaluation requires a valid UserContext instance.")

        with self._lock:
            results = {}
            for key, flag in self._flags.items():
                results[key] = evaluate_flag(flag, context)
            return results

    # -------------------------------------------------------------------------
    # Utility & Stats
    # -------------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Retrieve aggregated service metrics."""
        with self._lock:
            total = len(self._flags)
            active = sum(1 for f in self._flags.values() if f.enabled)
            total_rules = sum(len(f.rules) for f in self._flags.values())
            return {
                "total_flags": total,
                "active_flags": active,
                "inactive_flags": total - active,
                "total_rules": total_rules,
            }

    def clear(self) -> None:
        """Reset service state for test isolation."""
        with self._lock:
            self._flags.clear()
