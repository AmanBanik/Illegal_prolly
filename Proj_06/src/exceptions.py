"""Domain exceptions for the Feature Flag & Experiments service."""


class FeatureFlagError(Exception):
    """Base exception for all feature flag domain errors."""


class ValidationError(FeatureFlagError):
    """Raised when flag configuration, rule definitions, or payloads are invalid."""


class FlagNotFoundError(FeatureFlagError):
    """Raised when a requested feature flag key does not exist."""


class FlagAlreadyExistsError(FeatureFlagError):
    """Raised when attempting to create a flag with a key that already exists."""


class InvalidVariantError(FeatureFlagError):
    """Raised when a rule, rollout, or fallback references an undefined variant."""
