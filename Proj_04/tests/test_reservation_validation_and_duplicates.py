"""Tests for input validation, boundary checking, and duplicate reservation prevention."""

import pytest
from Proj_04.src.exceptions import DuplicateReservationError, ValidationError


def test_duplicate_active_reservation_for_same_user_raises_error(service, sample_session):
    service.make_reservation(sample_session.session_id, "user_repeated")

    with pytest.raises(DuplicateReservationError) as exc_info:
        service.make_reservation(sample_session.session_id, "user_repeated")
    assert "already holds an active reservation" in str(exc_info.value)


def test_re_reserve_after_cancellation_succeeds(service, sample_session):
    r1 = service.make_reservation(sample_session.session_id, "user_rebook")
    service.cancel_reservation(r1.reservation_id, "user_rebook")

    # Re-booking after cancelling must succeed
    r2 = service.make_reservation(sample_session.session_id, "user_rebook")
    assert r2.reservation_id != r1.reservation_id
    assert r2.status.value == "ACTIVE"


def test_reject_boolean_trap_in_capacity_and_strings(service):
    with pytest.raises(ValidationError):
        service.create_session(
            title=True,  # Boolean in string
            total_capacity=10,
            start_time="2026-11-01T10:00:00Z",
            end_time="2026-11-01T12:00:00Z",
        )

    with pytest.raises(ValidationError):
        service.create_session(
            title="Valid Title",
            total_capacity=True,  # isinstance(True, int) is True trap!
            start_time="2026-11-01T10:00:00Z",
            end_time="2026-11-01T12:00:00Z",
        )


def test_reject_zero_and_negative_capacity(service):
    with pytest.raises(ValidationError):
        service.create_session(
            title="Invalid",
            total_capacity=0,
            start_time="2026-11-01T10:00:00Z",
            end_time="2026-11-01T12:00:00Z",
        )

    with pytest.raises(ValidationError):
        service.create_session(
            title="Invalid",
            total_capacity=-5,
            start_time="2026-11-01T10:00:00Z",
            end_time="2026-11-01T12:00:00Z",
        )


def test_reject_invalid_timestamp_formats(service):
    with pytest.raises(ValidationError):
        service.create_session(
            title="Invalid Date",
            total_capacity=10,
            start_time="not-a-date",
            end_time="2026-11-01T12:00:00Z",
        )


def test_reject_end_time_before_or_equal_to_start_time(service):
    with pytest.raises(ValidationError):
        service.create_session(
            title="Backwards in time",
            total_capacity=10,
            start_time="2026-11-01T12:00:00Z",
            end_time="2026-11-01T10:00:00Z",
        )

    with pytest.raises(ValidationError):
        service.create_session(
            title="Zero duration",
            total_capacity=10,
            start_time="2026-11-01T12:00:00Z",
            end_time="2026-11-01T12:00:00Z",
        )


def test_reject_empty_and_whitespace_strings(service):
    with pytest.raises(ValidationError):
        service.create_session(
            title="   ",
            total_capacity=10,
            start_time="2026-11-01T10:00:00Z",
            end_time="2026-11-01T12:00:00Z",
        )

    with pytest.raises(ValidationError):
        service.make_reservation("sess_1", "   ")
