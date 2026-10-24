"""Tests for cancellation security, authorization, and idempotent capacity restoration."""

import pytest
from Proj_04.src.exceptions import (
    AlreadyCancelledError,
    ReservationNotFoundError,
    UnauthorizedCancellationError,
)
from Proj_04.src.models import ReservationStatus


def test_unauthorized_cancellation_rejected(service, sample_session):
    res = service.make_reservation(sample_session.session_id, "user_charlie")

    with pytest.raises(UnauthorizedCancellationError) as exc_info:
        service.cancel_reservation(res.reservation_id, "user_intruder")
    assert "not authorized" in str(exc_info.value)

    # State remains active
    current = service.get_reservation(res.reservation_id)
    assert current.status == ReservationStatus.ACTIVE
    assert service.get_session(sample_session.session_id).remaining_capacity == 4


def test_already_cancelled_rejected(service, sample_session):
    res = service.make_reservation(sample_session.session_id, "user_charlie")
    service.cancel_reservation(res.reservation_id, "user_charlie")

    # Second cancel attempt must fail cleanly
    with pytest.raises(AlreadyCancelledError):
        service.cancel_reservation(res.reservation_id, "user_charlie")

    # Capacity must NOT be restored a second time
    sess = service.get_session(sample_session.session_id)
    assert sess.remaining_capacity == 5


def test_cancel_nonexistent_reservation_raises_not_found(service):
    with pytest.raises(ReservationNotFoundError):
        service.cancel_reservation("res_nonexistent", "user_charlie")


def test_cancelled_reservation_retains_metadata(service, sample_session):
    res = service.make_reservation(sample_session.session_id, "user_dave")
    cancelled = service.cancel_reservation(res.reservation_id, "user_dave")

    assert cancelled.status == ReservationStatus.CANCELLED
    assert cancelled.cancelled_at is not None
    assert cancelled.created_at == res.created_at
    assert cancelled.user_id == "user_dave"


def test_remaining_capacity_never_exceeds_total_capacity(service, sample_session):
    # Total capacity is 5, remaining is 5
    res = service.make_reservation(sample_session.session_id, "user_1")
    service.cancel_reservation(res.reservation_id, "user_1")
    sess = service.get_session(sample_session.session_id)
    assert sess.remaining_capacity == 5
    assert sess.remaining_capacity <= sess.total_capacity
