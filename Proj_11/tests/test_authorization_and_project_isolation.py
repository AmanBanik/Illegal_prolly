"""Tests for project authorization, role enforcement, and multi-tenant project isolation."""

import pytest
from Proj_11.src.exceptions import AuthorizationError, IssueNotFoundError
from Proj_11.src.models import IssueStatus, ProjectRole


def test_role_hierarchy_permissions(service, sample_project):
    # 1. Viewer trying to create an issue -> Forbidden
    with pytest.raises(AuthorizationError) as exc_info:
        service.create_issue(
            project_id=sample_project,
            user_id="viewer_charlie",
            title="Unauthorized Task",
            description="Should fail",
        )
    assert "does not have permission" in str(exc_info.value)

    # 2. Member creates an issue -> Allowed
    issue = service.create_issue(
        project_id=sample_project,
        user_id="member_bob",
        title="Authorized Task",
        description="Allowed",
    )

    # 3. Viewer trying to update an issue -> Forbidden
    with pytest.raises(AuthorizationError):
        service.update_issue(
            project_id=sample_project,
            issue_id=issue.issue_id,
            user_id="viewer_charlie",
            expected_version=1,
            title="Viewer Hack",
        )

    # 4. Viewer trying to transition status -> Forbidden
    with pytest.raises(AuthorizationError):
        service.transition_status(
            project_id=sample_project,
            issue_id=issue.issue_id,
            user_id="viewer_charlie",
            expected_version=1,
            new_status=IssueStatus.IN_PROGRESS,
        )

    # 5. Viewer reading and listing -> Allowed
    read_issue = service.get_issue(sample_project, issue.issue_id, "viewer_charlie")
    assert read_issue == issue

    paginated = service.list_issues(sample_project, "viewer_charlie")
    assert len(paginated.items) >= 1

    # 6. Non-admin trying to add member -> Forbidden
    with pytest.raises(AuthorizationError):
        service.add_project_member(
            sample_project, actor_id="member_bob", user_id="new_user", role=ProjectRole.MEMBER
        )


def test_non_member_access_rejected(service, sample_project):
    with pytest.raises(AuthorizationError):
        service.get_project(sample_project, "stranger_eve")

    with pytest.raises(AuthorizationError):
        service.list_issues(sample_project, "stranger_eve")

    with pytest.raises(AuthorizationError):
        service.create_issue(sample_project, "stranger_eve", "Title", "Desc")


def test_cross_project_isolation(service, sample_project):
    # Create second project owned by user_carol
    p2 = service.create_project("proj_secret", "Secret Project", "user_carol")
    i2 = service.create_issue("proj_secret", "user_carol", "Secret Task", "Classified")

    # Member bob in sample_project cannot access p2
    with pytest.raises(AuthorizationError):
        service.get_project("proj_secret", "member_bob")

    with pytest.raises(AuthorizationError):
        service.list_issues("proj_secret", "member_bob")

    with pytest.raises(AuthorizationError):
        service.get_issue("proj_secret", i2.issue_id, "member_bob")

    # Carol querying i2 with sample_project id -> IssueNotFoundError (no leak)
    with pytest.raises(IssueNotFoundError):
        service.get_issue(sample_project, i2.issue_id, "admin_alice")
