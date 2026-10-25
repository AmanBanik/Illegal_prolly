"""Thread-safe in-memory storage engine for IssueHub."""

import base64
import json
import threading
from typing import Dict, List, Optional, Tuple

from Proj_11.src.exceptions import (
    DuplicateProjectError,
    IssueNotFoundError,
    ProjectNotFoundError,
    ValidationError,
)
from Proj_11.src.models import (
    IdempotencyRecord,
    Issue,
    IssueStatus,
    PaginatedIssues,
    Project,
    ProjectRole,
)


class IssueStorage:
    """Thread-safe in-memory storage providing snapshot isolation, indexing, and cursor pagination."""

    def __init__(self):
        self._lock = threading.RLock()
        self._projects: Dict[str, Project] = {}
        # (project_id, user_id) -> ProjectRole
        self._members: Dict[Tuple[str, str], ProjectRole] = {}
        # (project_id, issue_id) -> Issue
        self._issues: Dict[Tuple[str, str], Issue] = {}
        # (project_id, idempotency_key) -> IdempotencyRecord
        self._idempotency: Dict[Tuple[str, str], IdempotencyRecord] = {}
        # project_id -> List of issue_ids (in deterministic creation order)
        self._project_issue_order: Dict[str, List[str]] = {}

    def create_project(self, project: Project) -> Project:
        with self._lock:
            if project.project_id in self._projects:
                raise DuplicateProjectError(f"Project '{project.project_id}' already exists.")
            self._projects[project.project_id] = project
            self._members[(project.project_id, project.owner_id)] = ProjectRole.ADMIN
            self._project_issue_order[project.project_id] = []
            return project

    def get_project(self, project_id: str) -> Project:
        with self._lock:
            proj = self._projects.get(project_id)
            if not proj:
                raise ProjectNotFoundError(f"Project '{project_id}' not found.")
            return proj

    def set_member_role(self, project_id: str, user_id: str, role: ProjectRole) -> None:
        with self._lock:
            if project_id not in self._projects:
                raise ProjectNotFoundError(f"Project '{project_id}' not found.")
            self._members[(project_id, user_id)] = role

    def get_member_role(self, project_id: str, user_id: str) -> Optional[ProjectRole]:
        with self._lock:
            return self._members.get((project_id, user_id))

    def get_idempotency_record(
        self, project_id: str, key: str
    ) -> Optional[IdempotencyRecord]:
        with self._lock:
            return self._idempotency.get((project_id, key))

    def save_idempotency_record(self, record: IdempotencyRecord) -> None:
        with self._lock:
            self._idempotency[(record.project_id, record.key)] = record

    def save_issue(self, issue: Issue) -> Issue:
        with self._lock:
            key = (issue.project_id, issue.issue_id)
            is_new = key not in self._issues
            self._issues[key] = issue
            if is_new:
                if issue.project_id not in self._project_issue_order:
                    self._project_issue_order[issue.project_id] = []
                self._project_issue_order[issue.project_id].append(issue.issue_id)
            return issue

    def get_issue(self, project_id: str, issue_id: str) -> Issue:
        with self._lock:
            issue = self._issues.get((project_id, issue_id))
            if not issue:
                raise IssueNotFoundError(
                    f"Issue '{issue_id}' not found in project '{project_id}'."
                )
            return issue

    @staticmethod
    def encode_cursor(created_at: str, issue_id: str) -> str:
        payload = json.dumps({"t": created_at, "id": issue_id})
        return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("utf-8")

    @staticmethod
    def decode_cursor(cursor: str) -> Tuple[str, str]:
        try:
            raw = base64.urlsafe_b64decode(cursor.encode("utf-8")).decode("utf-8")
            data = json.loads(raw)
            return data["t"], data["id"]
        except Exception as e:
            raise ValidationError(f"Invalid pagination cursor: '{cursor}'.") from e

    def list_issues(
        self,
        project_id: str,
        status: Optional[IssueStatus] = None,
        limit: int = 10,
        cursor: Optional[str] = None,
    ) -> PaginatedIssues:
        with self._lock:
            if project_id not in self._projects:
                raise ProjectNotFoundError(f"Project '{project_id}' not found.")

            issue_ids = self._project_issue_order.get(project_id, [])
            all_issues = [self._issues[(project_id, i_id)] for i_id in issue_ids]

            # Filter by status if specified
            if status is not None:
                all_issues = [iss for iss in all_issues if iss.status == status]

            # Deterministic ordering by (created_at ASC, issue_id ASC)
            sorted_issues = sorted(all_issues, key=lambda x: (x.created_at, x.issue_id))
            total_count = len(sorted_issues)

            # Seek position if cursor is provided
            start_index = 0
            if cursor:
                cursor_ts, cursor_id = self.decode_cursor(cursor)
                for idx, iss in enumerate(sorted_issues):
                    if (iss.created_at, iss.issue_id) > (cursor_ts, cursor_id):
                        start_index = idx
                        break
                else:
                    start_index = len(sorted_issues)

            page_items = sorted_issues[start_index : start_index + limit]
            has_more = (start_index + limit) < len(sorted_issues)

            next_cursor = None
            if has_more and page_items:
                last_item = page_items[-1]
                next_cursor = self.encode_cursor(last_item.created_at, last_item.issue_id)

            return PaginatedIssues(
                items=page_items,
                next_cursor=next_cursor,
                has_more=has_more,
                total_count=total_count,
            )
