"""Concurrency and race-condition stress tests for SlotWise Reservation Service."""

from concurrent.futures import ThreadPoolExecutor, as_completed
import pytest
from Proj_04.src.exceptions import CapacityExceededError


def test_concurrent_reservations_strict_capacity_limit(service):
    """Verify that when 25 threads compete for 3 seats, exactly 3 win and zero overbooking occurs."""
    session = service.create_session(
        title="Exclusive Workshop",
        total_capacity=3,
        start_time="2026-11-20T14:00:00Z",
        end_time="2026-11-20T16:00:00Z",
    )

    num_threads = 25
    success_reservations = []
    exceeded_count = 0
    errors = []

    def book(user_idx: int):
        return service.make_reservation(session.session_id, f"user_{user_idx}")

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(book, i): i for i in range(num_threads)}
        for future in as_completed(futures):
            try:
                res = future.result()
                success_reservations.append(res)
            except CapacityExceededError:
                exceeded_count += 1
            except Exception as e:
                errors.append(e)

    # Invariants
    assert len(errors) == 0
    assert len(success_reservations) == 3
    assert exceeded_count == 22

    # Check database state
    sess = service.get_session(session.session_id)
    assert sess.remaining_capacity == 0

    report = service.get_session_capacity(session.session_id)
    assert report.total_capacity == 3
    assert report.active_reservations == 3
    assert report.remaining_capacity == 0
    assert report.is_consistent is True


def test_concurrent_reserve_and_cancel_interleaving(service):
    """Stress test with simultaneous reservations and cancellations maintaining state consistency."""
    session = service.create_session(
        title="Dynamic Session",
        total_capacity=5,
        start_time="2026-11-25T10:00:00Z",
        end_time="2026-11-25T12:00:00Z",
    )

    # Pre-seed 3 reservations
    r1 = service.make_reservation(session.session_id, "seed_user_1")
    r2 = service.make_reservation(session.session_id, "seed_user_2")
    r3 = service.make_reservation(session.session_id, "seed_user_3")

    initial_cancelled = [r1, r2]

    def cancel_task(res, u_id):
        try:
            return service.cancel_reservation(res.reservation_id, u_id)
        except Exception:
            return None

    def reserve_task(u_id):
        try:
            return service.make_reservation(session.session_id, u_id)
        except CapacityExceededError:
            return None

    tasks = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        # Submit cancels
        for res in initial_cancelled:
            tasks.append(executor.submit(cancel_task, res, res.user_id))
        # Submit new reserves
        for i in range(10):
            tasks.append(executor.submit(reserve_task, f"concurrent_user_{i}"))

        for f in as_completed(tasks):
            f.result()

    # Ground truth validation
    report = service.get_session_capacity(session.session_id)
    assert report.is_consistent is True
    assert 0 <= report.remaining_capacity <= 5
    assert report.remaining_capacity == 5 - report.active_reservations


def test_concurrent_multi_session_isolation(service):
    """Verify concurrent requests across separate sessions do not block or corrupt each other."""
    s1 = service.create_session(
        title="Session Alpha",
        total_capacity=4,
        start_time="2026-12-01T10:00:00Z",
        end_time="2026-12-01T12:00:00Z",
    )
    s2 = service.create_session(
        title="Session Beta",
        total_capacity=4,
        start_time="2026-12-01T14:00:00Z",
        end_time="2026-12-01T16:00:00Z",
    )

    def book(session_id: str, u_id: str):
        try:
            return service.make_reservation(session_id, u_id)
        except CapacityExceededError:
            return None

    with ThreadPoolExecutor(max_workers=10) as executor:
        f1 = [executor.submit(book, s1.session_id, f"u1_{i}") for i in range(10)]
        f2 = [executor.submit(book, s2.session_id, f"u2_{i}") for i in range(10)]
        for f in as_completed(f1 + f2):
            f.result()

    r1 = service.get_session_capacity(s1.session_id)
    r2 = service.get_session_capacity(s2.session_id)

    assert r1.active_reservations == 4
    assert r1.remaining_capacity == 0
    assert r1.is_consistent is True

    assert r2.active_reservations == 4
    assert r2.remaining_capacity == 0
    assert r2.is_consistent is True
