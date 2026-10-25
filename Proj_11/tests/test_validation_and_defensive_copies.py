"""Tests for type validation, boolean trap defenses, and defensive copy immutability."""

from dataclasses import FrozenInstanceError
import pytest
from Proj_11.src.exceptions import ValidationError


def test_reject_boolean_trap_in_strings_and_integers(service, sample_project):
    # Boolean passed as string field
    with pytest.raises(ValidationError):
        service.create_issue(
            project_id=sample_project,
            user_id="member_bob",
            title=True,  # Boolean trap
            description="Valid",
        )

    # Boolean passed as integer expected_version
    issue = service.create_issue(sample_project, "member_bob", "Title", "Desc")
    with pytest.raises(ValidationError):
        service.update_issue(
            project_id=sample_project,
            issue_id=issue.issue_id,
            user_id="member_bob",
            expected_version=True,  # isinstance(True, int) is True trap!
            title="New Title",
        )

    # Boolean passed as limit
    with pytest.raises(ValidationError):
        service.list_issues(sample_project, "viewer_charlie", limit=True)


def test_reject_empty_and_whitespace_fields(service, sample_project):
    with pytest.raises(ValidationError):
        service.create_issue(sample_project, "member_bob", "   ", "Desc")

    with pytest.raises(ValidationError):
        service.create_issue(sample_project, "member_bob", "Title", "   ")

    with pytest.raises(ValidationError):
        service.create_project("   ", "Name", "admin_alice")


def test_issue_immutability(service, sample_project):
    issue = service.create_issue(sample_project, "member_bob", "Immutable Task", "Desc")

    # Attempting to mutate frozen dataclass directly must raise FrozenInstanceError
    with pytest.raises(FrozenInstanceError):
        issue.title = "Hacked Title"

    with pytest.raises(FrozenInstanceError):
        issue.version = 999

    # Internal state remains pristine
    fetched = service.get_issue(sample_project, issue.issue_id, "member_bob")
    assert fetched.title == "Immutable Task"
    assert fetched.version == 1
