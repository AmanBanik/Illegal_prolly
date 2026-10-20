import hashlib
import os
import secrets
from datetime import datetime, timezone
from urllib.parse import urlencode, urlsplit, urlunsplit


def normalize_datetime(dt: datetime) -> datetime:
    """Normalizes any datetime (legacy naive or timezone-aware) to timezone-aware UTC.

    - If naive (no tzinfo), it is interpreted as UTC.
    - If aware, it is converted to UTC.
    """
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        # Legacy naive datetime - assume UTC
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def generate_secure_code(length: int = 6) -> str:
    """Generates a cryptographically secure numeric reset code using secrets."""
    digits = "0123456789"
    return "".join(secrets.choice(digits) for _ in range(length))


def build_reset_url(base_url: str, code: str, user_id: str) -> str:
    """Correctly constructs the password reset authentication URL.

    Safely handles trailing slashes, existing query parameters, and URL encoding
    without malforming the authentication gateway path.
    """
    clean_base = base_url.strip().rstrip("/")
    parsed = urlsplit(clean_base)

    # Determine endpoint path
    path = parsed.path.rstrip("/")
    if not path.endswith("reset-password"):
        path = f"{path}/reset-password" if path else "/reset-password"

    # Merge or append query parameters
    query_params = {"code": code, "user_id": user_id}
    query_string = urlencode(query_params)

    # Construct complete URL
    return urlunsplit((parsed.scheme, parsed.netloc, path, query_string, parsed.fragment))


def hash_password(password: str, salt: bytes | None = None) -> str:
    """Hashes a password using standard library PBKDF2-HMAC-SHA256 with a secure salt."""
    if salt is None:
        salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac(
        hash_name="sha256",
        password=password.encode("utf-8"),
        salt=salt,
        iterations=100_000,
    )
    # Stored as salt$hex_hash
    return f"{salt.hex()}${key.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verifies a password against the stored salt$hex_hash using constant-time comparison."""
    try:
        salt_hex, key_hex = stored_hash.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        expected_key = bytes.fromhex(key_hex)
    except (ValueError, TypeError):
        return False

    computed_key = hashlib.pbkdf2_hmac(
        hash_name="sha256",
        password=password.encode("utf-8"),
        salt=salt,
        iterations=100_000,
    )
    return secrets.compare_digest(computed_key, expected_key)
