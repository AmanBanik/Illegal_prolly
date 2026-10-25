"""Domain models for IssueHub Retry-Safe Issue Service."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class IssueStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


VALID_TRANSITIONS: Dict[IssueStatus, Set[IssueStatus]] = {
    IssueStatus.OPEN: {IssueStatus.IN_PROGRESS, IssueStatus.CLOSED},
    IssueStatus.IN_PROGRESS: {IssueStatus.RESOLVED, IssueStatus.OPEN, IssueStatus.CLOSED},
    IssueStatus.RESOLVED: {IssueStatus.CLOSED, IssueStatus.IN_PROGRESS},
    IssueStatus.CLOSED: {IssueStatus.OPEN},
}


class ProjectRole(str, Enum):
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"
    VIEWER = "VIEWER"


@dataclass(frozen=True)
class Project:
    project_id: str
    name: str
    owner_id: str
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "owner_id": self.owner_id,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class Issue:
    issue_id: str
    project_id: str
    title: str
    description: str
    status: IssueStatus
    creator_id: str
    assignee_id: Optional[str]
    version: int
    created_at: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "project_id": self.project_id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "creator_id": self.creator_id,
            "assignee_id": self.assignee_id,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class IdempotencyRecord:
    key: str
    project_id: str
    request_hash: str
    response_issue: Issue
    created_at: str


@dataclass(frozen=True)
class PaginatedIssues:
    items: List[Issue]
    next_cursor: Optional[str]
    has_more: bool
    total_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "items": [item.to_dict() for item in self.items],
            "next_cursor": self.next_cursor,
            "has_more": self.has_more,
            "total_count": self.total_count,
        }
