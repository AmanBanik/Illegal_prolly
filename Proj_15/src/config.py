import os
from dataclasses import dataclass
from typing import Optional
from .exceptions import ConfigurationError


@dataclass(frozen=True)
class PasswordResetConfig:
    """Immutable configuration snapshot for Password Reset Service."""

    auth_base_url: str = "https://auth.example.com"
    expiration_seconds: float = 30.0  # Exact 30-second validity window
    code_length: int = 6
    min_password_length: int = 8
    max_failed_attempts: int = 5

    @classmethod
    def from_env(cls, env_prefix: str = "PASSWORD_RESET_") -> "PasswordResetConfig":
        """Loads configuration from environment variables with strong validation."""
        auth_url = os.getenv(f"{env_prefix}AUTH_BASE_URL", "https://auth.example.com").strip()
        if not auth_url:
            raise ConfigurationError("AUTH_BASE_URL cannot be empty")

        exp_raw = os.getenv(f"{env_prefix}EXPIRATION_SECONDS", "30.0").strip()
        try:
            expiration_seconds = float(exp_raw)
            if expiration_seconds <= 0:
                raise ValueError
        except ValueError:
            raise ConfigurationError(f"Invalid EXPIRATION_SECONDS: {exp_raw}. Must be positive number.")

        len_raw = os.getenv(f"{env_prefix}CODE_LENGTH", "6").strip()
        try:
            code_length = int(len_raw)
            if code_length < 4 or code_length > 32:
                raise ValueError
        except ValueError:
            raise ConfigurationError(f"Invalid CODE_LENGTH: {len_raw}. Must be between 4 and 32.")

        min_pwd_raw = os.getenv(f"{env_prefix}MIN_PASSWORD_LENGTH", "8").strip()
        try:
            min_password_length = int(min_pwd_raw)
            if min_password_length < 6:
                raise ValueError
        except ValueError:
            raise ConfigurationError(f"Invalid MIN_PASSWORD_LENGTH: {min_pwd_raw}. Must be >= 6.")

        return cls(
            auth_base_url=auth_url,
            expiration_seconds=expiration_seconds,
            code_length=code_length,
            min_password_length=min_password_length,
        )
