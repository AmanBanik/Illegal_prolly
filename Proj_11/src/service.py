"""Application service layer for IssueHub Retry-Safe Issue Service."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional, Set

from Proj_11.src.exceptions import (
    AuthorizationError,
    IdempotencyConflictError,
    InvalidStatusTransitionError,
    ValidationError,
    VersionConflictError,
)
from Proj_11.src.models import (
    IdempotencyRecord,
    Issue,
    IssueStatus,
    PaginatedIssues,
    Project,
    ProjectRole,
    VALID_TRANSITIONS,
)
from Proj_11.src.storage import IssueStorage


class IssueService:
    """Orchestrates issue workflows, idempotency verification, optimistic locking, and authorization."""

    def __init__(self, storage: Optional[IssueStorage] = None):
        self.storage = storage or IssueStorage()

    # ---------------------------------------------------------
    # Input Validation Helpers
    # ---------------------------------------------------------

    def _validate_string(self, value: Any, field_name: str) -> str:
        if isinstance(value, bool) or not isinstance(value, str):
            raise ValidationError(
                f"Field '{field_name}' must be a string, got {type(value).__name__}."
            )
        cleaned = value.strip()
        if not cleaned:
            raise ValidationError(f"Field '{field_name}' cannot be empty or whitespace.")
        return cleaned

    def _validate_optional_string(self, value: Any, field_name: str) -> Optional[str]:
        if value is None:
            return None
        return self._validate_string(value, field_name)

    def _validate_version(self, value: Any) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValidationError(
                f"expected_version must be an integer, got {type(value).__name__}."
            )
        if value <= 0:
            raise ValidationError(f"expected_version must be positive (>= 1), got {value}.")
        return value

    def _validate_limit(self, limit: Any) -> int:
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise ValidationError(f"limit must be an integer, got {type(limit).__name__}.")
        if limit < 1 or limit > 100:
            raise ValidationError(f"limit must be between 1 and 100, got {limit}.")
        return limit

    @staticmethod
    def _hash_request(title: str, description: str, assignee_id: Optional[str]) -> str:
        payload = json.dumps(
            {"title": title, "description": description, "assignee_id": assignee_id},
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    # ---------------------------------------------------------
    # Authorization Helpers
    # ---------------------------------------------------------

    def _require_role(
        self, project_id: str, user_id: str, allowed_roles: Set[ProjectRole]
    ) -> ProjectRole:
        # First ensure project exists
        self.storage.get_project(project_id)
        role = self.storage.get_member_role(project_id, user_id)
        if not role or role not in allowed_roles:
            raise AuthorizationError(
                f"User '{user_id}' does not have permission in project '{project_id}'."
            )
        return role

    # ---------------------------------------------------------
    # Project & Membership Workflows
    # ---------------------------------------------------------

    def create_project(self, project_id: str, name: str, owner_id: str) -> Project:
        clean_pid = self._validate_string(project_id, "project_id")
        clean_name = self._validate_string(name, "name")
        clean_owner = self._validate_string(owner_id, "owner_id")
        created_at = datetime.now(timezone.utc).isoformat()

        project = Project(
            project_id=clean_pid,
            name=clean_name,
            owner_id=clean_owner,
            created_at=created_at,
        )
        return self.storage.create_project(project)

    def get_project(self, project_id: str, user_id: str) -> Project:
        clean_pid = self._validate_string(project_id, "project_id")
        clean_uid = self._validate_string(user_id, "user_id")
        self._require_role(
            clean_pid, clean_uid, {ProjectRole.ADMIN, ProjectRole.MEMBER, ProjectRole.VIEWER}
        )
        return self.storage.get_project(clean_pid)

    def add_project_member(
        self, project_id: str, actor_id: str, user_id: str, role: ProjectRole
    ) -> None:
        clean_pid = self._validate_string(project_id, "project_id")
        clean_actor = self._validate_string(actor_id, "actor_id")
        clean_uid = self._validate_string(user_id, "user_id")
        self._require_role(clean_pid, clean_actor, {ProjectRole.ADMIN})
        self.storage.set_member_role(clean_pid, clean_uid, role)

    # ---------------------------------------------------------
    # Issue Workflows with Idempotency & Optimistic Locking
    # ---------------------------------------------------------

    def create_issue(
        self,
        project_id: str,
        user_id: str,
        title: str,
        description: str,
        assignee_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        issue_id: Optional[str] = None,
    ) -> Issue:
        clean_pid = self._validate_string(project_id, "project_id")
        clean_uid = self._validate_string(user_id, "user_id")
        clean_title = self._validate_string(title, "title")
        clean_desc = self._validate_string(description, "description")
        clean_assignee = self._validate_optional_string(assignee_id, "assignee_id")
        clean_idem_key = self._validate_optional_string(idempotency_key, "idempotency_key")

        # Authorization: Member or Admin
        self._require_role(clean_pid, clean_uid, {ProjectRole.ADMIN, ProjectRole.MEMBER})

        req_hash = self._hash_request(clean_title, clean_desc, clean_assignee)

        # Idempotency Check
        if clean_idem_key:
            existing_record = self.storage.get_idempotency_record(clean_pid, clean_idem_key)
            if existing_record:
                if existing_record.request_hash == req_hash:
                    # Idempotent replay: return identical issue
                    return existing_record.response_issue
                else:
                    # Idempotency key reused with mismatched payload
                    raise IdempotencyConflictError(
                        f"Idempotency key '{clean_idem_key}' was previously used with different request parameters."
                    )

        now_ts = datetime.now(timezone.utc).isoformat()
        iid = (
            self._validate_string(issue_id, "issue_id")
            if issue_id
            else f"issue_{uuid.uuid4().hex[:12]}"
        )

        new_issue = Issue(
            issue_id=iid,
            project_id=clean_pid,
            title=clean_title,
            description=clean_desc,
            status=IssueStatus.OPEN,
            creator_id=clean_uid,
            assignee_id=clean_assignee,
            version=1,
            created_at=now_ts,
            updated_at=now_ts,
        )

        saved = self.storage.save_issue(new_issue)

        if clean_idem_key:
            self.storage.save_idempotency_record(
                IdempotencyRecord(
                    key=clean_idem_key,
                    project_id=clean_pid,
                    request_hash=req_hash,
                    response_issue=saved,
                    created_at=now_ts,
                )
            )

        return saved

    def get_issue(self, project_id: str, issue_id: str, user_id: str) -> Issue:
        clean_pid = self._validate_string(project_id, "project_id")
        clean_iid = self._validate_string(issue_id, "issue_id")
        clean_uid = self._validate_string(user_id, "user_id")

        self._require_role(
            clean_pid, clean_uid, {ProjectRole.ADMIN, ProjectRole.MEMBER, ProjectRole.VIEWER}
        )
        return self.storage.get_issue(clean_pid, clean_iid)

    def update_issue(
        self,
        project_id: str,
        issue_id: str,
        user_id: str,
        expected_version: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        assignee_id: Optional[str] = None,
    ) -> Issue:
        clean_pid = self._validate_string(project_id, "project_id")
        clean_iid = self._validate_string(issue_id, "issue_id")
        clean_uid = self._validate_string(user_id, "user_id")
        exp_ver = self._validate_version(expected_version)

        self._require_role(clean_pid, clean_uid, {ProjectRole.ADMIN, ProjectRole.MEMBER})

        # Atomic read-check-modify under storage lock
        with self.storage._lock:
            current = self.storage.get_issue(clean_pid, clean_iid)
            if current.version != exp_ver:
                raise VersionConflictError(
                    f"Version conflict on issue '{clean_iid}': expected version {exp_ver}, but current is {current.version}."
                )

            new_title = (
                self._validate_string(title, "title") if title is not None else current.title
            )
            new_desc = (
                self._validate_string(description, "description")
                if description is not None
                else current.description
            )
            new_assignee = (
                self._validate_optional_string(assignee_id, "assignee_id")
                if assignee_id is not None
                else current.assignee_id
            )

            updated = Issue(
                issue_id=current.issue_id,
                project_id=current.project_id,
                title=new_title,
                description=new_desc,
                status=current.status,
                creator_id=current.creator_id,
                assignee_id=new_assignee,
                version=current.version + 1,
                created_at=current.created_at,
                updated_at=datetime.now(timezone.utc).isoformat(),
            )
            return self.storage.save_issue(updated)

    def transition_status(
        self,
        project_id: str,
        issue_id: str,
        user_id: str,
        expected_version: int,
        new_status: IssueStatus,
    ) -> Issue:
        clean_pid = self._validate_string(project_id, "project_id")
        clean_iid = self._validate_string(issue_id, "issue_id")
        clean_uid = self._validate_string(user_id, "user_id")
        exp_ver = self._validate_version(expected_version)

        if not isinstance(new_status, IssueStatus):
            try:
                new_status = IssueStatus(new_status)
            except ValueError:
                raise ValidationError(f"Invalid issue status '{new_status}'.")

        self._require_role(clean_pid, clean_uid, {ProjectRole.ADMIN, ProjectRole.MEMBER})

        with self.storage._lock:
            current = self.storage.get_issue(clean_pid, clean_iid)
            if current.version != exp_ver:
                raise VersionConflictError(
                    f"Version conflict on issue '{clean_iid}': expected version {exp_ver}, but current is {current.version}."
                )

            allowed = VALID_TRANSITIONS.get(current.status, set())
            if new_status not in allowed:
                raise InvalidStatusTransitionError(
                    f"Invalid status transition from '{current.status.value}' to '{new_status.value}'."
                )

            updated = Issue(
                issue_id=current.issue_id,
                project_id=current.project_id,
                title=current.title,
                description=current.description,
                status=new_status,
                creator_id=current.creator_id,
                assignee_id=current.assignee_id,
                version=current.version + 1,
                created_at=current.created_at,
                updated_at=datetime.now(timezone.utc).isoformat(),
            )
            return self.storage.save_issue(updated)

    def list_issues(
        self,
        project_id: str,
        user_id: str,
        status: Optional[IssueStatus] = None,
        limit: int = 10,
        cursor: Optional[str] = None,
    ) -> PaginatedIssues:
        clean_pid = self._validate_string(project_id, "project_id")
        clean_uid = self._validate_string(user_id, "user_id")
        clean_limit = self._validate_limit(limit)

        if status is not None and not isinstance(status, IssueStatus):
            try:
                status = IssueStatus(status)
            except ValueError:
                raise ValidationError(f"Invalid status filter '{status}'.")

        self._require_role(
            clean_pid, clean_uid, {ProjectRole.ADMIN, ProjectRole.MEMBER, ProjectRole.VIEWER}
        )
        return self.storage.list_issues(
            project_id=clean_pid, status=status, limit=clean_limit, cursor=cursor
        )
