from datetime import datetime, timedelta, timezone
import pytest
from Proj_15.src.exceptions import (
    CodeAlreadyUsedError,
    ExpiredCodeError,
    InvalidCodeError,
    UserNotFoundError,
    WeakPasswordError,
)
from Proj_15.src.utils import verify_password


def test_password_reset_happy_path(service, storage):
    t0 = datetime(2026, 10, 20, 10, 0, 0, tzinfo=timezone.utc)

    # 1. Request reset
    resp = service.request_password_reset("alice@example.com", current_time=t0)
    assert resp.reset_code is not None
    assert len(resp.reset_code) == 6
    assert resp.validity_seconds == 30.0
    assert resp.expires_at == t0 + timedelta(seconds=30.0)
    assert "usr_001" in resp.reset_url
    assert resp.reset_code in resp.reset_url

    # 2. Validate code within window (t0 + 15s)
    t_val = t0 + timedelta(seconds=15)
    assert service.validate_reset_code("alice@example.com", resp.reset_code, current_time=t_val) is True

    # 3. Reset password within window (t0 + 25s)
    t_reset = t0 + timedelta(seconds=25)
    success = service.reset_password(
        "alice@example.com",
        resp.reset_code,
        "NewBrandPass2026!",
        current_time=t_reset,
    )
    assert success is True

    # 4. Check persistence in storage
    user = storage.get_user_by_id("usr_001")
    assert verify_password("NewBrandPass2026!", user.password_hash) is True
    assert verify_password("OldPassword123!", user.password_hash) is False


def test_exact_30_second_validity_window(service):
    t0 = datetime(2026, 10, 20, 10, 0, 0, tzinfo=timezone.utc)
    resp = service.request_password_reset("alice@example.com", current_time=t0)

    # Exactly at 30.0s boundary -> allowed
    t_exact = t0 + timedelta(seconds=30.0)
    assert service.validate_reset_code("usr_001", resp.reset_code, current_time=t_exact) is True

    # At 30.1s -> expired
    t_expired = t0 + timedelta(seconds=30.1)
    with pytest.raises(ExpiredCodeError):
        service.validate_reset_code("usr_001", resp.reset_code, current_time=t_expired)

    # Reset attempt after expiration fails
    with pytest.raises(ExpiredCodeError):
        service.reset_password("usr_001", resp.reset_code, "ValidNewPass123!", current_time=t_expired)


def test_replay_attack_prevention_one_time_consumption(service):
    t0 = datetime(2026, 10, 20, 10, 0, 0, tzinfo=timezone.utc)
    resp = service.request_password_reset("alice@example.com", current_time=t0)

    # First reset succeeds
    service.reset_password("usr_001", resp.reset_code, "NewPassSuccess1!", current_time=t0 + timedelta(seconds=5))

    # Second replay attempt MUST fail with CodeAlreadyUsedError
    with pytest.raises(CodeAlreadyUsedError):
        service.reset_password("usr_001", resp.reset_code, "ReplayedPassAttack2!", current_time=t0 + timedelta(seconds=10))

    # Validating the already used code also fails
    with pytest.raises(CodeAlreadyUsedError):
        service.validate_reset_code("usr_001", resp.reset_code, current_time=t0 + timedelta(seconds=12))


def test_subsequent_request_invalidates_previous_code(service):
    t0 = datetime(2026, 10, 20, 10, 0, 0, tzinfo=timezone.utc)

    # First request
    resp1 = service.request_password_reset("alice@example.com", current_time=t0)

    # Second request 5 seconds later
    resp2 = service.request_password_reset("alice@example.com", current_time=t0 + timedelta(seconds=5))

    # Attempting to use Code 1 should fail because it was invalidated by Code 2
    with pytest.raises(CodeAlreadyUsedError):
        service.reset_password("usr_001", resp1.reset_code, "AttemptWithOldCode1!", current_time=t0 + timedelta(seconds=10))

    # Using Code 2 succeeds
    assert service.reset_password("usr_001", resp2.reset_code, "SuccessWithNewCode2!", current_time=t0 + timedelta(seconds=12)) is True


def test_user_isolation(service):
    t0 = datetime(2026, 10, 20, 10, 0, 0, tzinfo=timezone.utc)
    resp_alice = service.request_password_reset("alice@example.com", current_time=t0)

    # Bob attempts to use Alice's code
    with pytest.raises(InvalidCodeError):
        service.reset_password("bob@example.com", resp_alice.reset_code, "HackedPass123!", current_time=t0 + timedelta(seconds=5))


def test_legacy_naive_timestamp_support(service):
    # Pass naive datetime (no timezone info)
    t0_naive = datetime(2026, 10, 20, 10, 0, 0)
    resp = service.request_password_reset("alice@example.com", current_time=t0_naive)

    t_val_naive = datetime(2026, 10, 20, 10, 0, 15)
    # Must succeed without offset-naive vs offset-aware comparison TypeError
    assert service.validate_reset_code("alice@example.com", resp.reset_code, current_time=t_val_naive) is True


def test_weak_password_validation(service):
    t0 = datetime(2026, 10, 20, 10, 0, 0, tzinfo=timezone.utc)
    resp = service.request_password_reset("alice@example.com", current_time=t0)

    with pytest.raises(WeakPasswordError):
        service.reset_password("usr_001", resp.reset_code, "short", current_time=t0 + timedelta(seconds=5))


def test_nonexistent_user(service):
    with pytest.raises(UserNotFoundError):
        service.request_password_reset("ghost@example.com")
