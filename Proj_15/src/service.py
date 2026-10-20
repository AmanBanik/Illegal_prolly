from datetime import datetime, timedelta, timezone
from typing import Optional
from .config import PasswordResetConfig
from .exceptions import (
    CodeAlreadyUsedError,
    ExpiredCodeError,
    InvalidCodeError,
    RateLimitExceededError,
    UserNotFoundError,
    WeakPasswordError,
)
from .models import ResetCodeRecord, ResetRequestResponse, User
from .storage import InMemoryDatabase, StorageBoundary
from .utils import (
    build_reset_url,
    generate_secure_code,
    hash_password,
    normalize_datetime,
    verify_password,
)


class PasswordResetService:
    """Production-grade Password Reset Service.

    Guarantees:
    - Exact 30-second token validity window.
    - Full support for both timezone-aware and legacy offset-naive timestamps.
    - Zero replay attacks via atomic one-time code consumption.
    - Correct authentication URL generation.
    - Safe state persistence and snapshot isolation across service instances.
    """

    def __init__(
        self,
        storage: Optional[StorageBoundary] = None,
        config: Optional[PasswordResetConfig] = None,
    ):
        self._storage = storage or InMemoryDatabase()
        self._config = config or PasswordResetConfig()

    @property
    def config(self) -> PasswordResetConfig:
        return self._config

    @property
    def storage(self) -> StorageBoundary:
        return self._storage

    def _resolve_user(self, user_id_or_email: str) -> User:
        """Resolves user by email or user_id."""
        clean_input = user_id_or_email.strip()
        if "@" in clean_input:
            user = self._storage.get_user_by_email(clean_input)
        else:
            user = self._storage.get_user_by_id(clean_input)

        if not user:
            raise UserNotFoundError(f"User not found for identifier: {clean_input}")
        return user

    def request_password_reset(
        self,
        email: str,
        current_time: Optional[datetime] = None,
    ) -> ResetRequestResponse:
        """Initiates a password recovery request for the given email address.

        - Enforces user existence.
        - Invalidates any previous pending reset codes for this user.
        - Emits a secure 6-digit code with an exact 30-second expiration window.
        - Returns the properly constructed reset URL and code.
        """
        user = self._resolve_user(email)
        now = normalize_datetime(current_time or datetime.now(timezone.utc))
        expires_at = now + timedelta(seconds=self._config.expiration_seconds)

        # Invalidate any previously issued active codes for this user
        self._storage.revoke_all_codes_for_user(user.user_id)

        code = generate_secure_code(self._config.code_length)
        record = ResetCodeRecord(
            code=code,
            user_id=user.user_id,
            created_at=now,
            expires_at=expires_at,
            is_used=False,
            failed_attempts=0,
        )
        self._storage.save_reset_code(record)

        reset_url = build_reset_url(self._config.auth_base_url, code, user.user_id)

        return ResetRequestResponse(
            reset_url=reset_url,
            reset_code=code,
            expires_at=expires_at,
            validity_seconds=self._config.expiration_seconds,
        )

    def validate_reset_code(
        self,
        user_id_or_email: str,
        code: str,
        current_time: Optional[datetime] = None,
    ) -> bool:
        """Validates code correctness, expiration window, and single-use status.

        Supports both offset-aware and legacy offset-naive timestamps.
        """
        user = self._resolve_user(user_id_or_email)
        now = normalize_datetime(current_time or datetime.now(timezone.utc))

        record = self._storage.get_reset_code(user.user_id, code.strip())
        if not record:
            raise InvalidCodeError("Invalid reset code")

        if record.is_used:
            raise CodeAlreadyUsedError("This reset code has already been consumed and cannot be replayed")

        if record.failed_attempts >= self._config.max_failed_attempts:
            raise RateLimitExceededError("Maximum validation attempts exceeded for this code")

        # Expiration check: strictly valid within 30-second window
        record_expires_at = normalize_datetime(record.expires_at)
        if now > record_expires_at:
            raise ExpiredCodeError("The 30-second validity window for this reset code has expired")

        return True

    def reset_password(
        self,
        user_id_or_email: str,
        code: str,
        new_password: str,
        current_time: Optional[datetime] = None,
    ) -> bool:
        """Consumes the reset code and updates the user's password in storage.

        Enforces atomic single-use code consumption to eliminate race conditions.
        """
        if len(new_password) < self._config.min_password_length:
            raise WeakPasswordError(
                f"Password must be at least {self._config.min_password_length} characters"
            )

        user = self._resolve_user(user_id_or_email)
        now = normalize_datetime(current_time or datetime.now(timezone.utc))

        try:
            self.validate_reset_code(user.user_id, code, current_time=now)
        except InvalidCodeError:
            self._storage.increment_failed_attempts(user.user_id, code.strip())
            raise

        # Atomically consume the code (single-use)
        consumed = self._storage.mark_code_used(user.user_id, code.strip())
        if not consumed:
            raise CodeAlreadyUsedError("This reset code has already been consumed")

        # Update persisted password state
        new_hash = hash_password(new_password)
        updated = self._storage.update_user_password(user.user_id, new_hash, updated_at=now)
        if not updated:
            raise UserNotFoundError(f"Failed to persist password update for user {user.user_id}")

        return True
