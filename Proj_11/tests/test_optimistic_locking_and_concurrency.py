"""Tests for optimistic concurrency control (OCC), version checks, and race conditions."""

from concurrent.futures import ThreadPoolExecutor, as_completed
import pytest
from Proj_11.src.exceptions import VersionConflictError
from Proj_11.src.models import IssueStatus


def test_optimistic_locking_stale_version_rejected(service, sample_project):
    issue = service.create_issue(
        project_id=sample_project,
        user_id="member_bob",
        title="Initial Task",
        description="Version 1 initial",
    )
    assert issue.version == 1

    # First update succeeds, advancing version to 2
    u1 = service.update_issue(
        project_id=sample_project,
        issue_id=issue.issue_id,
        user_id="member_bob",
        expected_version=1,
        title="First Update",
    )
    assert u1.version == 2

    # Attempting update with stale expected_version = 1 must be rejected
    with pytest.raises(VersionConflictError) as exc_info:
        service.update_issue(
            project_id=sample_project,
            issue_id=issue.issue_id,
            user_id="member_bob",
            expected_version=1,  # Stale!
            title="Stale Update Attempt",
        )
    assert "expected version 1, but current is 2" in str(exc_info.value)

    # Issue state remains at version 2
    current = service.get_issue(sample_project, issue.issue_id, "member_bob")
    assert current.title == "First Update"
    assert current.version == 2


def test_concurrent_updates_single_winner(service, sample_project):
    """Verify that when 25 threads compete to update an issue at version 1, exactly 1 wins."""
    issue = service.create_issue(
        project_id=sample_project,
        user_id="member_bob",
        title="Concurrent Target",
        description="Base payload",
    )
    assert issue.version == 1

    num_threads = 25
    successes = []
    conflicts = 0
    errors = []

    def attempt_update(thread_idx: int):
        return service.update_issue(
            project_id=sample_project,
            issue_id=issue.issue_id,
            user_id="member_bob",
            expected_version=1,  # All threads see version 1
            title=f"Updated by Thread {thread_idx}",
        )

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(attempt_update, i): i for i in range(num_threads)}
        for future in as_completed(futures):
            try:
                res = future.result()
                successes.append(res)
            except VersionConflictError:
                conflicts += 1
            except Exception as e:
                errors.append(e)

    # Invariants
    assert len(errors) == 0
    assert len(successes) == 1
    assert conflicts == 24

    # Final state
    final_issue = service.get_issue(sample_project, issue.issue_id, "member_bob")
    assert final_issue.version == 2
    assert final_issue.title.startswith("Updated by Thread ")


def test_concurrent_transitions_single_winner(service, sample_project):
    """Verify concurrent status transitions under OCC enforce single-winner execution."""
    issue = service.create_issue(
        project_id=sample_project,
        user_id="member_bob",
        title="Status Target",
        description="Transition test",
    )
    assert issue.status == IssueStatus.OPEN
    assert issue.version == 1

    num_threads = 20
    successes = []
    conflicts = 0

    def attempt_transition():
        return service.transition_status(
            project_id=sample_project,
            issue_id=issue.issue_id,
            user_id="member_bob",
            expected_version=1,
            new_status=IssueStatus.IN_PROGRESS,
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(attempt_transition) for _ in range(num_threads)]
        for f in as_completed(futures):
            try:
                res = f.result()
                successes.append(res)
            except VersionConflictError:
                conflicts += 1

    assert len(successes) == 1
    assert conflicts == 19

    final_issue = service.get_issue(sample_project, issue.issue_id, "member_bob")
    assert final_issue.status == IssueStatus.IN_PROGRESS
    assert final_issue.version == 2
