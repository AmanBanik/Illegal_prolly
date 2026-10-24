"""Tests for core reservation lifecycle workflows."""

import pytest
from Proj_04.src.exceptions import SessionNotFoundError, ReservationNotFoundError
from Proj_04.src.models import ReservationStatus


def test_create_and_get_session(service):
    session = service.create_session(
        title="Python Performance Tuning",
        total_capacity=10,
        start_time="2026-11-15T09:00:00Z",
        end_time="2026-11-15T11:00:00Z",
    )
    assert session.title == "Python Performance Tuning"
    assert session.total_capacity == 10
    assert session.remaining_capacity == 10

    fetched = service.get_session(session.session_id)
    assert fetched == session


def test_get_nonexistent_session_raises_not_found(service):
    with pytest.raises(SessionNotFoundError):
        service.get_session("non_existent_sess")


def test_list_sessions_order(service):
    s2 = service.create_session(
        title="Session 2",
        total_capacity=10,
        start_time="2026-12-01T10:00:00Z",
        end_time="2026-12-01T12:00:00Z",
    )
    s1 = service.create_session(
        title="Session 1",
        total_capacity=10,
        start_time="2026-11-01T10:00:00Z",
        end_time="2026-11-01T12:00:00Z",
    )
    sessions = service.list_sessions()
    assert len(sessions) == 2
    # Chronological start_time ordering
    assert sessions[0].session_id == s1.session_id
    assert sessions[1].session_id == s2.session_id


def test_reservation_creation_and_capacity_decrement(service, sample_session):
    res = service.make_reservation(sample_session.session_id, "user_alice")
    assert res.session_id == sample_session.session_id
    assert res.user_id == "user_alice"
    assert res.status == ReservationStatus.ACTIVE
    assert res.cancelled_at is None

    # Check updated session capacity
    sess = service.get_session(sample_session.session_id)
    assert sess.remaining_capacity == 4

    # Ground truth report
    report = service.get_session_capacity(sample_session.session_id)
    assert report.total_capacity == 5
    assert report.active_reservations == 1
    assert report.cancelled_reservations == 0
    assert report.remaining_capacity == 4
    assert report.is_consistent is True


def test_reservation_cancellation_and_capacity_restoration(service, sample_session):
    res = service.make_reservation(sample_session.session_id, "user_alice")
    assert service.get_session(sample_session.session_id).remaining_capacity == 4

    cancelled = service.cancel_reservation(res.reservation_id, "user_alice")
    assert cancelled.status == ReservationStatus.CANCELLED
    assert cancelled.cancelled_at is not None

    # Session capacity must be restored
    sess = service.get_session(sample_session.session_id)
    assert sess.remaining_capacity == 5

    report = service.get_session_capacity(sample_session.session_id)
    assert report.active_reservations == 0
    assert report.cancelled_reservations == 1
    assert report.remaining_capacity == 5
    assert report.is_consistent is True


def test_user_reservation_history(service, sample_session):
    s2 = service.create_session(
        title="Second Course",
        total_capacity=10,
        start_time="2026-11-20T10:00:00Z",
        end_time="2026-11-20T12:00:00Z",
    )
    r1 = service.make_reservation(sample_session.session_id, "user_bob")
    r2 = service.make_reservation(s2.session_id, "user_bob")

    history = service.list_user_reservations("user_bob")
    assert len(history) == 2
    res_ids = [r.reservation_id for r in history]
    assert r1.reservation_id in res_ids
    assert r2.reservation_id in res_ids
