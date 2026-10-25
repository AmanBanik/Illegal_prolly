"""Flask REST API adapter for IssueHub Retry-Safe Issue Service."""

from typing import Optional

from flask import Flask, jsonify, request

from Proj_11.src.exceptions import (
    AuthorizationError,
    DuplicateProjectError,
    IdempotencyConflictError,
    InvalidStatusTransitionError,
    IssueNotFoundError,
    ProjectNotFoundError,
    ValidationError,
    VersionConflictError,
)
from Proj_11.src.models import ProjectRole
from Proj_11.src.service import IssueService


def create_app(service: Optional[IssueService] = None) -> Flask:
    app = Flask(__name__)
    svc = service or IssueService()

    def _get_user_id() -> str:
        uid = request.headers.get("X-User-ID") or request.args.get("user_id")
        if not uid:
            raise ValidationError("Missing required user identification header 'X-User-ID'.")
        return uid.strip()

    @app.errorhandler(ValidationError)
    def handle_validation_error(e: ValidationError):
        return jsonify({"error": "VALIDATION_ERROR", "message": str(e)}), 400

    @app.errorhandler(AuthorizationError)
    def handle_auth_error(e: AuthorizationError):
        return jsonify({"error": "AUTHORIZATION_ERROR", "message": str(e)}), 403

    @app.errorhandler(ProjectNotFoundError)
    def handle_project_not_found(e: ProjectNotFoundError):
        return jsonify({"error": "PROJECT_NOT_FOUND", "message": str(e)}), 404

    @app.errorhandler(IssueNotFoundError)
    def handle_issue_not_found(e: IssueNotFoundError):
        return jsonify({"error": "ISSUE_NOT_FOUND", "message": str(e)}), 404

    @app.errorhandler(VersionConflictError)
    def handle_version_conflict(e: VersionConflictError):
        return jsonify({"error": "VERSION_CONFLICT", "message": str(e)}), 409

    @app.errorhandler(IdempotencyConflictError)
    def handle_idempotency_conflict(e: IdempotencyConflictError):
        return jsonify({"error": "IDEMPOTENCY_CONFLICT", "message": str(e)}), 409

    @app.errorhandler(InvalidStatusTransitionError)
    def handle_invalid_transition(e: InvalidStatusTransitionError):
        return jsonify({"error": "INVALID_STATUS_TRANSITION", "message": str(e)}), 409

    @app.errorhandler(DuplicateProjectError)
    def handle_duplicate_project(e: DuplicateProjectError):
        return jsonify({"error": "DUPLICATE_PROJECT", "message": str(e)}), 409

    # ---------------------------------------------------------
    # Project Endpoints
    # ---------------------------------------------------------

    @app.route("/api/projects", methods=["POST"])
    def create_project():
        data = request.get_json(force=True, silent=True) or {}
        user_id = _get_user_id()
        proj = svc.create_project(
            project_id=data.get("project_id"),
            name=data.get("name"),
            owner_id=user_id,
        )
        return jsonify(proj.to_dict()), 201

    @app.route("/api/projects/<project_id>", methods=["GET"])
    def get_project(project_id: str):
        user_id = _get_user_id()
        proj = svc.get_project(project_id, user_id)
        return jsonify(proj.to_dict()), 200

    @app.route("/api/projects/<project_id>/members", methods=["POST"])
    def add_member(project_id: str):
        data = request.get_json(force=True, silent=True) or {}
        actor_id = _get_user_id()
        role_str = data.get("role", "MEMBER")
        try:
            role = ProjectRole(role_str)
        except ValueError:
            raise ValidationError(f"Invalid member role '{role_str}'.")

        svc.add_project_member(
            project_id=project_id,
            actor_id=actor_id,
            user_id=data.get("user_id"),
            role=role,
        )
        return jsonify({"status": "MEMBER_ADDED"}), 200

    # ---------------------------------------------------------
    # Issue Endpoints
    # ---------------------------------------------------------

    @app.route("/api/projects/<project_id>/issues", methods=["POST"])
    def create_issue(project_id: str):
        data = request.get_json(force=True, silent=True) or {}
        user_id = _get_user_id()
        idempotency_key = (
            request.headers.get("Idempotency-Key") or data.get("idempotency_key")
        )

        issue = svc.create_issue(
            project_id=project_id,
            user_id=user_id,
            title=data.get("title"),
            description=data.get("description"),
            assignee_id=data.get("assignee_id"),
            idempotency_key=idempotency_key,
        )
        return jsonify(issue.to_dict()), 201

    @app.route("/api/projects/<project_id>/issues/<issue_id>", methods=["GET"])
    def get_issue(project_id: str, issue_id: str):
        user_id = _get_user_id()
        issue = svc.get_issue(project_id, issue_id, user_id)
        return jsonify(issue.to_dict()), 200

    @app.route("/api/projects/<project_id>/issues/<issue_id>", methods=["PUT"])
    def update_issue(project_id: str, issue_id: str):
        data = request.get_json(force=True, silent=True) or {}
        user_id = _get_user_id()

        # Support If-Match header (e.g. '"1"' or '1') or body expected_version
        expected_version = data.get("expected_version")
        if_match = request.headers.get("If-Match")
        if if_match is not None:
            clean_if_match = if_match.strip().strip('"')
            try:
                expected_version = int(clean_if_match)
            except ValueError:
                raise ValidationError(f"Invalid If-Match header value '{if_match}'.")

        if expected_version is None:
            raise ValidationError("Missing expected_version for optimistic concurrency control.")

        updated = svc.update_issue(
            project_id=project_id,
            issue_id=issue_id,
            user_id=user_id,
            expected_version=expected_version,
            title=data.get("title"),
            description=data.get("description"),
            assignee_id=data.get("assignee_id"),
        )
        return jsonify(updated.to_dict()), 200

    @app.route("/api/projects/<project_id>/issues/<issue_id>/transition", methods=["POST"])
    def transition_issue_status(project_id: str, issue_id: str):
        data = request.get_json(force=True, silent=True) or {}
        user_id = _get_user_id()
        expected_version = data.get("expected_version")
        if expected_version is None:
            raise ValidationError("Missing expected_version for status transition.")

        updated = svc.transition_status(
            project_id=project_id,
            issue_id=issue_id,
            user_id=user_id,
            expected_version=expected_version,
            new_status=data.get("new_status"),
        )
        return jsonify(updated.to_dict()), 200

    @app.route("/api/projects/<project_id>/issues", methods=["GET"])
    def list_issues(project_id: str):
        user_id = _get_user_id()
        status_filter = request.args.get("status")
        cursor = request.args.get("cursor")
        limit_raw = request.args.get("limit", "10")
        try:
            limit = int(limit_raw)
        except ValueError:
            raise ValidationError(f"Invalid limit parameter '{limit_raw}'.")

        res = svc.list_issues(
            project_id=project_id,
            user_id=user_id,
            status=status_filter,
            limit=limit,
            cursor=cursor,
        )
        return jsonify(res.to_dict()), 200

    return app
