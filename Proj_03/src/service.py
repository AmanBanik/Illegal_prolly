import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Set
from urllib.parse import urlparse
from .exceptions import (
    CodeAlreadyExistsError,
    CollisionExhaustionError,
    ForbiddenError,
    InvalidShortCodeError,
    InvalidUrlError,
    LinkExpiredError,
    LinkNotFoundError,
    ValidationError,
)
from .models import AggregateStats, CreateLinkRequest, LinkMetadata, LinkRecord
from .repository import LinkRepository

BASE62_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
RESERVED_CODES: Set[str] = {
    "api",
    "stats",
    "health",
    "metrics",
    "admin",
    "static",
    "favicon.ico",
    "swagger",
    "docs",
}
CUSTOM_CODE_REGEX = re.compile(r"^[a-zA-Z0-9_-]{3,30}$")


class UrlShortenerService:
    """Core domain service for URL shortening, redirection, and lifecycle management."""

    def __init__(
        self,
        repository: LinkRepository,
        default_code_length: int = 6,
        max_collision_retries: int = 10,
    ):
        self._repo = repository
        self._code_length = default_code_length
        self._max_retries = max_collision_retries

    @property
    def repository(self) -> LinkRepository:
        return self._repo

    def validate_url(self, url: str) -> str:
        """Validates that a URL is a well-formed HTTP/HTTPS address."""
        if not url or not isinstance(url, str):
            raise InvalidUrlError("URL must be a non-empty string")

        clean_url = url.strip()
        if len(clean_url) > 2048:
            raise InvalidUrlError("URL exceeds maximum length of 2048 characters")

        try:
            parsed = urlparse(clean_url)
            if parsed.scheme.lower() not in ("http", "https"):
                raise InvalidUrlError("URL scheme must be http or https")
            if not parsed.netloc:
                raise InvalidUrlError("URL must include a valid host/domain name")
        except Exception as e:
            if isinstance(e, InvalidUrlError):
                raise
            raise InvalidUrlError(f"Malformed URL: {e}") from e

        return clean_url

    def validate_custom_code(self, custom_code: str) -> str:
        """Validates custom short-code format and prevents route collisions with reserved words."""
        if not custom_code or not isinstance(custom_code, str):
            raise InvalidShortCodeError("Custom code must be a non-empty string")

        clean_code = custom_code.strip()
        if not CUSTOM_CODE_REGEX.match(clean_code):
            raise InvalidShortCodeError(
                "Custom code must be 3-30 characters long and contain only alphanumeric, dash, or underscore characters"
            )

        if clean_code.lower() in RESERVED_CODES:
            raise InvalidShortCodeError(f"Custom code '{clean_code}' is a reserved route keyword")

        return clean_code

    def _generate_unique_code(self) -> str:
        """Generates a random Base62 short code with collision detection and retry."""
        for _ in range(self._max_retries):
            code = "".join(secrets.choice(BASE62_ALPHABET) for _ in range(self._code_length))
            if code.lower() not in RESERVED_CODES and not self._repo.code_exists(code):
                return code

        raise CollisionExhaustionError(
            f"Failed to generate unique short code after {self._max_retries} attempts"
        )

    def create_short_link(
        self,
        request: CreateLinkRequest,
        base_url: str = "http://localhost:5000",
        current_time: Optional[datetime] = None,
    ) -> LinkMetadata:
        """Creates and persists a new shortened URL mapping."""
        valid_url = self.validate_url(request.original_url)

        user_id = request.user_id.strip() if request.user_id else "anonymous"
        now = current_time or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        # Handle TTL
        expires_at = None
        if request.ttl_seconds is not None:
            if request.ttl_seconds <= 0:
                raise ValidationError("ttl_seconds must be a positive integer")
            expires_at = now + timedelta(seconds=request.ttl_seconds)

        # Handle custom code vs auto-generation
        if request.custom_code:
            short_code = self.validate_custom_code(request.custom_code)
            if self._repo.code_exists(short_code):
                raise CodeAlreadyExistsError(f"Short code '{short_code}' is already in use")

            record = LinkRecord(
                short_code=short_code,
                original_url=valid_url,
                user_id=user_id,
                created_at=now,
                expires_at=expires_at,
                hit_count=0,
                is_deleted=False,
            )
            self._repo.save_link(record)
            return self._record_to_metadata(record, base_url, now)
        else:
            for _ in range(self._max_retries):
                short_code = self._generate_unique_code()
                record = LinkRecord(
                    short_code=short_code,
                    original_url=valid_url,
                    user_id=user_id,
                    created_at=now,
                    expires_at=expires_at,
                    hit_count=0,
                    is_deleted=False,
                )
                try:
                    self._repo.save_link(record)
                    return self._record_to_metadata(record, base_url, now)
                except CodeAlreadyExistsError:
                    continue

            raise CollisionExhaustionError(
                f"Failed to generate unique short code after {self._max_retries} attempts"
            )

    def get_destination_and_record_hit(
        self,
        short_code: str,
        current_time: Optional[datetime] = None,
    ) -> str:
        """Retrieves original URL and atomically increments hit counter.

        Raises:
            LinkNotFoundError: if code does not exist or was deleted.
            LinkExpiredError: if code passed its TTL expiration date.
        """
        now = current_time or datetime.now(timezone.utc)
        record = self._repo.get_by_code(short_code.strip())

        if not record or record.is_deleted:
            raise LinkNotFoundError(f"Short code '{short_code}' not found")

        if record.is_expired(now):
            raise LinkExpiredError(f"Short code '{short_code}' has expired")

        # Concurrency-safe atomic hit increment
        self._repo.increment_hit(short_code.strip())
        return record.original_url

    def get_link_metadata(
        self,
        short_code: str,
        base_url: str = "http://localhost:5000",
        current_time: Optional[datetime] = None,
    ) -> LinkMetadata:
        """Fetches metadata and usage statistics for a short link."""
        now = current_time or datetime.now(timezone.utc)
        record = self._repo.get_by_code(short_code.strip())

        if not record or record.is_deleted:
            raise LinkNotFoundError(f"Short code '{short_code}' not found")

        return self._record_to_metadata(record, base_url, now)

    def delete_link(self, short_code: str, requesting_user_id: str) -> None:
        """Deletes a short link with ownership authorization verification."""
        clean_code = short_code.strip()
        record = self._repo.get_by_code(clean_code)

        if not record or record.is_deleted:
            raise LinkNotFoundError(f"Short code '{clean_code}' not found")

        if record.user_id != requesting_user_id.strip():
            raise ForbiddenError("You do not have permission to delete this link")

        self._repo.soft_delete(clean_code)

    def get_aggregate_stats(
        self,
        user_id: Optional[str] = None,
        current_time: Optional[datetime] = None,
    ) -> AggregateStats:
        """Retrieves system-wide or user-specific aggregate metrics."""
        return self._repo.get_aggregate_stats(user_id=user_id, current_time=current_time)

    def _record_to_metadata(
        self, record: LinkRecord, base_url: str, current_time: datetime
    ) -> LinkMetadata:
        clean_base = base_url.rstrip("/")
        short_url = f"{clean_base}/{record.short_code}"
        return LinkMetadata(
            short_code=record.short_code,
            original_url=record.original_url,
            short_url=short_url,
            user_id=record.user_id,
            created_at=record.created_at.isoformat(),
            expires_at=record.expires_at.isoformat() if record.expires_at else None,
            hit_count=record.hit_count,
            is_active=record.is_active(current_time),
        )
