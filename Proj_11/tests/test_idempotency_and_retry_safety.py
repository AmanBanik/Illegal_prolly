"""Tests for idempotency key mechanics, duplicate retries, and payload conflict detection."""

import pytest
from Proj_11.src.exceptions import IdempotencyConflictError, ValidationError


def test_idempotent_creation_replay_returns_identical_issue(service, sample_project):
    key = "idem_tx_12345"
    i1 = service.create_issue(
        project_id=sample_project,
        user_id="member_bob",
        title="Deploy Redis Sentinel",
        description="Configure automatic failover across 3 nodes.",
        assignee_id="member_bob",
        idempotency_key=key,
    )

    # Simulated network timeout / client retry with identical key & payload
    i2 = service.create_issue(
        project_id=sample_project,
        user_id="member_bob",
        title="Deploy Redis Sentinel",
        description="Configure automatic failover across 3 nodes.",
        assignee_id="member_bob",
        idempotency_key=key,
    )

    assert i1 == i2
    assert i1.issue_id == i2.issue_id
    assert i1.version == 1
    assert i2.version == 1
    assert i1.created_at == i2.created_at


def test_idempotency_key_mismatch_payload_raises_conflict(service, sample_project):
    key = "idem_tx_conflict"
    service.create_issue(
        project_id=sample_project,
        user_id="member_bob",
        title="Original Title",
        description="Original Description",
        idempotency_key=key,
    )

    # Reusing the same key with changed title
    with pytest.raises(IdempotencyConflictError) as exc_info:
        service.create_issue(
            project_id=sample_project,
            user_id="member_bob",
            title="Altered Title",  # Mismatched!
            description="Original Description",
            idempotency_key=key,
        )
    assert "previously used with different request parameters" in str(exc_info.value)


def test_idempotency_scoped_by_project(service, sample_project):
    # Create second project
    p2 = service.create_project("proj_secondary", "Secondary Project", "admin_alice")
    service.add_project_member("proj_secondary", "admin_alice", "member_bob", role="MEMBER")

    key = "shared_key_across_projects"
    i1 = service.create_issue(
        project_id=sample_project,
        user_id="member_bob",
        title="Task Alpha",
        description="Alpha desc",
        idempotency_key=key,
    )

    # Same key in different project must create independent issue without collision
    i2 = service.create_issue(
        project_id="proj_secondary",
        user_id="member_bob",
        title="Task Beta",
        description="Beta desc",
        idempotency_key=key,
    )

    assert i1.project_id == sample_project
    assert i2.project_id == "proj_secondary"
    assert i1.issue_id != i2.issue_id


def test_failed_request_does_not_poison_idempotency_key(service, sample_project):
    key = "idem_fail_recovery"
    # Empty title triggers ValidationError
    with pytest.raises(ValidationError):
        service.create_issue(
            project_id=sample_project,
            user_id="member_bob",
            title="   ",  # Invalid
            description="Valid description",
            idempotency_key=key,
        )

    # Subsequent request with same key and valid title must succeed
    i_recovered = service.create_issue(
        project_id=sample_project,
        user_id="member_bob",
        title="Valid Title Now",
        description="Valid description",
        idempotency_key=key,
    )
    assert i_recovered.title == "Valid Title Now"
    assert i_recovered.version == 1
