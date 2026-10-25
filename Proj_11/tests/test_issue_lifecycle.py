"""Tests for core issue lifecycle, creation, retrieval, and status transitions."""

import pytest
from Proj_11.src.exceptions import (
    InvalidStatusTransitionError,
    IssueNotFoundError,
    ProjectNotFoundError,
)
from Proj_11.src.models import IssueStatus


def test_create_and_get_issue_happy_path(service, sample_project):
    issue = service.create_issue(
        project_id=sample_project,
        user_id="member_bob",
        title="Fix NullPointer in Auth Middleware",
        description="Stack trace observed when Authorization header is absent.",
        assignee_id="member_bob",
    )

    assert issue.project_id == sample_project
    assert issue.title == "Fix NullPointer in Auth Middleware"
    assert issue.status == IssueStatus.OPEN
    assert issue.version == 1
    assert issue.creator_id == "member_bob"
    assert issue.assignee_id == "member_bob"
    assert issue.created_at == issue.updated_at

    fetched = service.get_issue(sample_project, issue.issue_id, "member_bob")
    assert fetched == issue


def test_get_nonexistent_issue_raises_not_found(service, sample_project):
    with pytest.raises(IssueNotFoundError):
        service.get_issue(sample_project, "issue_ghost", "member_bob")


def test_update_issue_fields_and_version_increment(service, sample_project):
    issue = service.create_issue(
        project_id=sample_project,
        user_id="member_bob",
        title="Initial Title",
        description="Initial Description",
    )
    assert issue.version == 1

    updated = service.update_issue(
        project_id=sample_project,
        issue_id=issue.issue_id,
        user_id="member_bob",
        expected_version=1,
        title="Updated Title",
        description="Updated Description",
        assignee_id="admin_alice",
    )

    assert updated.title == "Updated Title"
    assert updated.description == "Updated Description"
    assert updated.assignee_id == "admin_alice"
    assert updated.version == 2
    assert updated.status == IssueStatus.OPEN


def test_valid_status_transition_sequence(service, sample_project):
    # OPEN -> IN_PROGRESS -> RESOLVED -> CLOSED -> OPEN
    issue = service.create_issue(
        project_id=sample_project,
        user_id="member_bob",
        title="Lifecycle Issue",
        description="Testing complete state machine sequence",
    )
    assert issue.status == IssueStatus.OPEN
    assert issue.version == 1

    t1 = service.transition_status(
        sample_project, issue.issue_id, "member_bob", 1, IssueStatus.IN_PROGRESS
    )
    assert t1.status == IssueStatus.IN_PROGRESS
    assert t1.version == 2

    t2 = service.transition_status(
        sample_project, issue.issue_id, "member_bob", 2, IssueStatus.RESOLVED
    )
    assert t2.status == IssueStatus.RESOLVED
    assert t2.version == 3

    t3 = service.transition_status(
        sample_project, issue.issue_id, "member_bob", 3, IssueStatus.CLOSED
    )
    assert t3.status == IssueStatus.CLOSED
    assert t3.version == 4

    # Reopening
    t4 = service.transition_status(
        sample_project, issue.issue_id, "member_bob", 4, IssueStatus.OPEN
    )
    assert t4.status == IssueStatus.OPEN
    assert t4.version == 5


def test_invalid_status_transition_rejected(service, sample_project):
    issue = service.create_issue(
        project_id=sample_project,
        user_id="member_bob",
        title="Jump Status Issue",
        description="Testing illegal transition",
    )

    # OPEN -> RESOLVED is illegal (must go through IN_PROGRESS)
    with pytest.raises(InvalidStatusTransitionError) as exc_info:
        service.transition_status(
            sample_project, issue.issue_id, "member_bob", 1, IssueStatus.RESOLVED
        )
    assert "Invalid status transition" in str(exc_info.value)

    # Verify version was NOT incremented and status unchanged
    current = service.get_issue(sample_project, issue.issue_id, "member_bob")
    assert current.status == IssueStatus.OPEN
    assert current.version == 1
