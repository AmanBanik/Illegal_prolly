from datetime import datetime, timedelta, timezone
import pytest
from Proj_03.src.exceptions import (
    CodeAlreadyExistsError,
    ForbiddenError,
    LinkExpiredError,
    LinkNotFoundError,
    ValidationError,
)
from Proj_03.src.models import CreateLinkRequest


def test_create_and_redirect_lifecycle(service):
    req = CreateLinkRequest(
        original_url="https://news.ycombinator.com",
        user_id="user_alice",
    )
    meta = service.create_short_link(req)
    assert meta.short_code is not None
    assert len(meta.short_code) == 6
    assert meta.hit_count == 0
    assert meta.is_active is True

    # First redirect
    dest = service.get_destination_and_record_hit(meta.short_code)
    assert dest == "https://news.ycombinator.com"

    # Second redirect
    service.get_destination_and_record_hit(meta.short_code)

    # Check updated metadata
    updated_meta = service.get_link_metadata(meta.short_code)
    assert updated_meta.hit_count == 2


def test_custom_code_duplicate_conflict(service):
    req1 = CreateLinkRequest(
        original_url="https://python.org",
        user_id="user_alice",
        custom_code="python_docs",
    )
    service.create_short_link(req1)

    # Second creation with identical custom code must raise CodeAlreadyExistsError
    req2 = CreateLinkRequest(
        original_url="https://google.com",
        user_id="user_bob",
        custom_code="python_docs",
    )
    with pytest.raises(CodeAlreadyExistsError):
        service.create_short_link(req2)


def test_ttl_expiration_logic(service):
    t0 = datetime(2026, 10, 21, 12, 0, 0, tzinfo=timezone.utc)
    req = CreateLinkRequest(
        original_url="https://temporary.org",
        user_id="user_alice",
        ttl_seconds=30,
    )
    meta = service.create_short_link(req, current_time=t0)

    # Within TTL window (t0 + 20s) -> allowed
    dest = service.get_destination_and_record_hit(meta.short_code, current_time=t0 + timedelta(seconds=20))
    assert dest == "https://temporary.org"

    # Beyond TTL window (t0 + 35s) -> raises LinkExpiredError
    with pytest.raises(LinkExpiredError):
        service.get_destination_and_record_hit(meta.short_code, current_time=t0 + timedelta(seconds=35))


def test_invalid_ttl_value(service):
    req = CreateLinkRequest(
        original_url="https://valid.org",
        user_id="user_alice",
        ttl_seconds=-10,
    )
    with pytest.raises(ValidationError):
        service.create_short_link(req)


def test_ownership_authorization_and_deletion(service):
    req = CreateLinkRequest(
        original_url="https://private.org",
        user_id="user_owner",
    )
    meta = service.create_short_link(req)

    # Intruder tries to delete -> ForbiddenError
    with pytest.raises(ForbiddenError):
        service.delete_link(meta.short_code, requesting_user_id="user_intruder")

    # Owner deletes -> succeeds
    service.delete_link(meta.short_code, requesting_user_id="user_owner")

    # Subsequent redirect -> LinkNotFoundError
    with pytest.raises(LinkNotFoundError):
        service.get_destination_and_record_hit(meta.short_code)


def test_aggregate_stats_calculation(service):
    t0 = datetime(2026, 10, 21, 10, 0, 0, tzinfo=timezone.utc)
    # Link 1: Active
    m1 = service.create_short_link(CreateLinkRequest("https://a.com", "user_1"), current_time=t0)
    service.get_destination_and_record_hit(m1.short_code, current_time=t0)
    service.get_destination_and_record_hit(m1.short_code, current_time=t0)

    # Link 2: Expired
    m2 = service.create_short_link(CreateLinkRequest("https://b.com", "user_1", ttl_seconds=10), current_time=t0)

    # Link 3: Deleted
    m3 = service.create_short_link(CreateLinkRequest("https://c.com", "user_2"), current_time=t0)
    service.delete_link(m3.short_code, requesting_user_id="user_2")

    # Evaluate stats at t0 + 20s
    stats = service.get_aggregate_stats(current_time=t0 + timedelta(seconds=20))
    assert stats.total_links == 3
    assert stats.active_links == 1
    assert stats.expired_links == 1
    assert stats.deleted_links == 1
    assert stats.total_hits == 2
