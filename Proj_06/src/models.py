"""Domain models and value objects for feature flags, rules, and evaluations."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Dict, List, Optional


class Operator(str, Enum):
    """Supported rule evaluation operators."""

    EQUALS = "EQUALS"
    NOT_EQUALS = "NOT_EQUALS"
    IN = "IN"
    NOT_IN = "NOT_IN"
    CONTAINS = "CONTAINS"
    STARTS_WITH = "STARTS_WITH"
    ENDS_WITH = "ENDS_WITH"
    GREATER_THAN = "GREATER_THAN"
    GREATER_THAN_OR_EQUAL = "GREATER_THAN_OR_EQUAL"
    LESS_THAN = "LESS_THAN"
    LESS_THAN_OR_EQUAL = "LESS_THAN_OR_EQUAL"


class EvaluationReason(str, Enum):
    """Reason code indicating how a variant was resolved."""

    DISABLED = "DISABLED"
    RULE_MATCH = "RULE_MATCH"
    PERCENTAGE_ROLLOUT = "PERCENTAGE_ROLLOUT"
    DEFAULT_FALLBACK = "DEFAULT_FALLBACK"


@dataclass
class Variant:
    """Represents a feature variation and its optional payload attachment."""

    key: str
    attachment: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "attachment": copy.deepcopy(self.attachment),
        }


@dataclass
class RuleCondition:
    """A single attribute comparison condition within a targeting rule."""

    attribute: str
    operator: Operator
    value: Any

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attribute": self.attribute,
            "operator": self.operator.value,
            "value": copy.deepcopy(self.value),
        }


@dataclass
class TargetingRule:
    """An ordered targeting rule evaluated with first-match-wins semantics.

    All conditions within a rule must be satisfied (AND condition).
    """

    id: str
    conditions: List[RuleCondition]
    variant_key: str
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "conditions": [c.to_dict() for c in self.conditions],
            "variant_key": self.variant_key,
            "description": self.description,
        }


@dataclass
class RolloutVariant:
    """A weighted variation allocation in a percentage rollout."""

    variant_key: str
    weight: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "variant_key": self.variant_key,
            "weight": self.weight,
        }


@dataclass
class RolloutConfig:
    """Deterministic percentage-based rollout bucketing configuration."""

    variants: List[RolloutVariant]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "variants": [v.to_dict() for v in self.variants],
        }


@dataclass
class FeatureFlag:
    """Full configuration specification of a feature flag."""

    key: str
    name: str
    description: str
    enabled: bool
    variants: List[Variant]
    default_variant: str
    rules: List[TargetingRule] = field(default_factory=list)
    rollout: Optional[RolloutConfig] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "variants": [v.to_dict() for v in self.variants],
            "default_variant": self.default_variant,
            "rules": [r.to_dict() for r in self.rules],
            "rollout": self.rollout.to_dict() if self.rollout else None,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def copy(self) -> FeatureFlag:
        """Create an isolated deep copy of the feature flag."""
        return copy.deepcopy(self)


@dataclass
class UserContext:
    """Evaluation context representing user attributes."""

    user_id: str
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "attributes": copy.deepcopy(self.attributes),
        }


@dataclass
class EvaluationResult:
    """The resolved variation and diagnostic metadata for a flag evaluation."""

    flag_key: str
    enabled: bool
    variant_key: str
    attachment: Optional[Any]
    reason: EvaluationReason
    rule_id: Optional[str] = None
    bucket_value: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "flag_key": self.flag_key,
            "enabled": self.enabled,
            "variant_key": self.variant_key,
            "attachment": copy.deepcopy(self.attachment),
            "reason": self.reason.value,
            "rule_id": self.rule_id,
            "bucket_value": self.bucket_value,
        }
