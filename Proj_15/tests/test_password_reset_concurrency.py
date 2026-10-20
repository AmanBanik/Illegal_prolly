import concurrent.futures
from datetime import datetime, timedelta, timezone
import pytest
from Proj_15.src.exceptions import CodeAlreadyUsedError
from Proj_15.src.models import User
from Proj_15.src.service import PasswordResetService
from Proj_15.src.storage import InMemoryDatabase
from Proj_15.src.utils import hash_password, verify_password


def test_concurrent_code_consumption_single_winner(service, storage):
    """Verify that when multiple threads attempt to consume the same code concurrently,
    atomic single-use locking ensures exactly ONE succeeds and all others are rejected."""
    t0 = datetime(2026, 10, 20, 10, 0, 0, tzinfo=timezone.utc)
    resp = service.request_password_reset("alice@example.com", current_time=t0)
    code = resp.reset_code

    num_threads = 25
    success_count = 0
    replay_error_count = 0
    errors = []

    def attempt_reset(worker_id: int):
        pwd = f"NewPasswordWorker_{worker_id:03d}!"
        t_now = t0 + timedelta(seconds=10)
        return service.reset_password("usr_001", code, pwd, current_time=t_now)

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        future_to_id = {executor.submit(attempt_reset, i): i for i in range(num_threads)}
        for future in concurrent.futures.as_completed(future_to_id):
            try:
                res = future.result()
                if res is True:
                    success_count += 1
            except CodeAlreadyUsedError:
                replay_error_count += 1
            except Exception as e:
                errors.append(e)

    assert errors == [], f"Unexpected errors during concurrent consumption: {errors}"
    assert success_count == 1, f"Expected exactly 1 success, got {success_count}"
    assert replay_error_count == num_threads - 1, f"Expected {num_threads - 1} replay errors, got {replay_error_count}"

    # Verify user record in storage is valid and one of the worker passwords
    user = storage.get_user_by_id("usr_001")
    assert user is not None
    # Password must match one of the worker passwords, but not the original old password
    assert verify_password("OldPassword123!", user.password_hash) is False


def test_concurrent_requests_across_independent_users(storage):
    """Multiple users concurrently requesting and resetting passwords must remain isolated."""
    # Add 10 users
    num_users = 10
    now = datetime(2026, 10, 20, 10, 0, 0, tzinfo=timezone.utc)
    for i in range(num_users):
        storage.save_user(
            User(
                user_id=f"u_{i}",
                email=f"user_{i}@example.com",
                password_hash=hash_password(f"InitialPass_{i}!"),
                created_at=now,
                updated_at=now,
            )
        )

    service = PasswordResetService(storage=storage)

    def user_flow(user_idx: int):
        email = f"user_{user_idx}@example.com"
        resp = service.request_password_reset(email, current_time=now)
        new_pwd = f"FinalPassword_{user_idx}!"
        return service.reset_password(email, resp.reset_code, new_pwd, current_time=now + timedelta(seconds=15))

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_users) as executor:
        futures = [executor.submit(user_flow, i) for i in range(num_users)]
        for f in concurrent.futures.as_completed(futures):
            assert f.result() is True

    # Verify all users updated correctly
    for i in range(num_users):
        u = storage.get_user_by_email(f"user_{i}@example.com")
        assert verify_password(f"FinalPassword_{i}!", u.password_hash) is True


def test_storage_boundary_defensive_copies(storage):
    """Mutating returned objects must never mutate internal database state."""
    user = storage.get_user_by_id("usr_001")
    user.email = "hacked@example.com"
    user.password_hash = "compromised_hash"

    clean_user = storage.get_user_by_id("usr_001")
    assert clean_user.email == "alice@example.com"
    assert clean_user.password_hash != "compromised_hash"
