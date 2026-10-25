"""Tests for cursor-based pagination, deterministic ordering, and status filtering."""

import pytest
from Proj_11.src.exceptions import ValidationError
from Proj_11.src.models import IssueStatus


def test_cursor_pagination_multi_page_traversal(service, sample_project):
    # Create 25 issues
    created_ids = []
    for i in range(25):
        iss = service.create_issue(
            project_id=sample_project,
            user_id="member_bob",
            title=f"Issue {i:02d}",
            description=f"Pagination test item {i}",
        )
        created_ids.append(iss.issue_id)

    # Page 1: limit 10
    p1 = service.list_issues(sample_project, "viewer_charlie", limit=10)
    assert len(p1.items) == 10
    assert p1.has_more is True
    assert p1.next_cursor is not None
    assert p1.total_count == 25

    # Page 2: limit 10
    p2 = service.list_issues(sample_project, "viewer_charlie", limit=10, cursor=p1.next_cursor)
    assert len(p2.items) == 10
    assert p2.has_more is True
    assert p2.next_cursor is not None

    # Page 3: limit 10 -> remaining 5
    p3 = service.list_issues(sample_project, "viewer_charlie", limit=10, cursor=p2.next_cursor)
    assert len(p3.items) == 5
    assert p3.has_more is False
    assert p3.next_cursor is None

    # Verify set union and uniqueness across all pages
    all_retrieved = [item.issue_id for item in p1.items + p2.items + p3.items]
    assert len(all_retrieved) == 25
    assert set(all_retrieved) == set(created_ids)


def test_cursor_pagination_status_filtering(service, sample_project):
    # Create 6 OPEN, 4 IN_PROGRESS
    open_ids = []
    in_prog_ids = []

    for i in range(6):
        iss = service.create_issue(
            sample_project, "member_bob", f"Open {i}", "desc"
        )
        open_ids.append(iss.issue_id)

    for i in range(4):
        iss = service.create_issue(
            sample_project, "member_bob", f"Prog {i}", "desc"
        )
        service.transition_status(
            sample_project, iss.issue_id, "member_bob", 1, IssueStatus.IN_PROGRESS
        )
        in_prog_ids.append(iss.issue_id)

    # Filter by IN_PROGRESS with limit 2
    p1 = service.list_issues(
        sample_project, "viewer_charlie", status=IssueStatus.IN_PROGRESS, limit=2
    )
    assert len(p1.items) == 2
    assert p1.has_more is True
    assert all(item.status == IssueStatus.IN_PROGRESS for item in p1.items)

    p2 = service.list_issues(
        sample_project, "viewer_charlie", status=IssueStatus.IN_PROGRESS, limit=2, cursor=p1.next_cursor
    )
    assert len(p2.items) == 2
    assert p2.has_more is False
    assert p2.next_cursor is None
    assert all(item.status == IssueStatus.IN_PROGRESS for item in p2.items)

    retrieved = [item.issue_id for item in p1.items + p2.items]
    assert set(retrieved) == set(in_prog_ids)


def test_cursor_pagination_boundary_limits(service, sample_project):
    with pytest.raises(ValidationError):
        service.list_issues(sample_project, "viewer_charlie", limit=0)

    with pytest.raises(ValidationError):
        service.list_issues(sample_project, "viewer_charlie", limit=101)


def test_invalid_cursor_rejected(service, sample_project):
    with pytest.raises(ValidationError) as exc_info:
        service.list_issues(sample_project, "viewer_charlie", cursor="invalid-not-base64")
    assert "Invalid pagination cursor" in str(exc_info.value)
