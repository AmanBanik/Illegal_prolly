from datetime import datetime, timezone, timedelta
import pytest
from Proj_15.src.utils import normalize_datetime, build_reset_url, generate_secure_code, hash_password, verify_password


def test_normalize_datetime_aware_utc():
    aware_utc = datetime(2026, 10, 20, 12, 0, 0, tzinfo=timezone.utc)
    res = normalize_datetime(aware_utc)
    assert res == aware_utc
    assert res.tzinfo == timezone.utc


def test_normalize_datetime_legacy_naive():
    naive = datetime(2026, 10, 20, 12, 0, 0)
    res = normalize_datetime(naive)
    assert res.tzinfo == timezone.utc
    assert res.year == 2026
    assert res.hour == 12

    # Verification: can safely compare with aware datetime without TypeError
    aware = datetime(2026, 10, 20, 12, 0, 10, tzinfo=timezone.utc)
    assert res < aware


def test_normalize_datetime_offset_conversion():
    ist = timezone(timedelta(hours=5, minutes=30))
    dt_ist = datetime(2026, 10, 20, 17, 30, 0, tzinfo=ist)
    res = normalize_datetime(dt_ist)
    assert res.tzinfo == timezone.utc
    assert res.hour == 12
    assert res.minute == 0


def test_build_reset_url_edge_cases():
    # Case 1: Standard URL
    url1 = build_reset_url("https://auth.example.com", "123456", "usr_001")
    assert url1 == "https://auth.example.com/reset-password?code=123456&user_id=usr_001"

    # Case 2: Trailing slash in base URL (should not create double slash //)
    url2 = build_reset_url("https://auth.example.com/", "123456", "usr_001")
    assert "//reset-password" not in url2
    assert url2 == "https://auth.example.com/reset-password?code=123456&user_id=usr_001"

    # Case 3: URL with subpath
    url3 = build_reset_url("https://auth.example.com/api/v2", "999888", "usr_002")
    assert url3 == "https://auth.example.com/api/v2/reset-password?code=999888&user_id=usr_002"


def test_generate_secure_code_format_and_uniqueness():
    code1 = generate_secure_code(6)
    code2 = generate_secure_code(6)
    assert len(code1) == 6
    assert code1.isdigit()
    assert len(code2) == 6
    assert code2.isdigit()
    # High entropy ensures different codes
    codes = {generate_secure_code(6) for _ in range(100)}
    assert len(codes) >= 95


def test_password_hashing_and_verification():
    raw = "SuperSecretPassword123!"
    h = hash_password(raw)
    assert verify_password(raw, h) is True
    assert verify_password("WrongPassword!", h) is False
