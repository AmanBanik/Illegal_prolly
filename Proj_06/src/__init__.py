"""Feature Flag & Experimentation Engine.

Provides thread-safe in-memory feature flag configuration management,
ordered targeting rule evaluation with first-match semantics, deterministic
percentage rollout bucketing (SHA-256), defensive copy snapshot isolation,
and a RESTful API gateway.
"""

from .exceptions import (
    FeatureFlagError,
    FlagAlreadyExistsError,
    FlagNotFoundError,
    InvalidVariantError,
    ValidationError,
)
from .models import (
    EvaluationReason,
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
from .service import FeatureFlagService

__all__ = [
    "FeatureFlagService",
    "FeatureFlag",
    "Variant",
    "TargetingRule",
    "RuleCondition",
    "RolloutConfig",
    "RolloutVariant",
    "UserContext",
    "EvaluationResult",
    "Operator",
    "EvaluationReason",
    "FeatureFlagError",
    "ValidationError",
    "FlagNotFoundError",
    "FlagAlreadyExistsError",
    "InvalidVariantError",
]
