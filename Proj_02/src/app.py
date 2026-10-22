"""Flask REST API adapter for the Comments & Replies discussion service."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
from flask import Flask, jsonify, request

from .exceptions import (
    CommentNotFoundError,
    CommentServiceError,
    ConflictError,
    InvalidHierarchyError,
    PostNotFoundError,
    ResourceNotFoundError,
    ValidationError,
)
from .service import CommentService


def create_app(service: Optional[CommentService] = None) -> Flask:
    """Application factory for the Discussion Platform REST API."""
    app = Flask(__name__)
    svc = service if service is not None else CommentService()

    # -------------------------------------------------------------------------
    # Error Handlers
    # -------------------------------------------------------------------------

    @app.errorhandler(ValidationError)
    def handle_validation_error(error: ValidationError) -> Tuple[Any, int]:
        return jsonify({"status": "error", "type": "ValidationError", "message": str(error)}), 400

    @app.errorhandler(InvalidHierarchyError)
    def handle_hierarchy_error(error: InvalidHierarchyError) -> Tuple[Any, int]:
        return (
            jsonify({"status": "error", "type": "InvalidHierarchyError", "message": str(error)}),
            400,
        )

    @app.errorhandler(ResourceNotFoundError)
    def handle_not_found(error: ResourceNotFoundError) -> Tuple[Any, int]:
        return (
            jsonify({"status": "error", "type": error.__class__.__name__, "message": str(error)}),
            404,
        )

    @app.errorhandler(ConflictError)
    def handle_conflict(error: ConflictError) -> Tuple[Any, int]:
        return jsonify({"status": "error", "type": "ConflictError", "message": str(error)}), 409

    # -------------------------------------------------------------------------
    # Routes
    # -------------------------------------------------------------------------

    @app.route("/api/posts/<post_id>/comments", methods=["POST"])
    def add_comment(post_id: str) -> Tuple[Any, int]:
        """Add a comment to a specified post."""
        payload: Dict[str, Any] = request.get_json(silent=True) or {}
        author_id = payload.get("author_id")
        content = payload.get("content")

        if author_id is None or content is None:
            raise ValidationError("Payload must include both 'author_id' and 'content'.")

        comment = svc.add_comment(post_id=post_id, author_id=author_id, content=content)
        return jsonify({"status": "success", "data": comment.to_dict()}), 201

    @app.route("/api/posts/<post_id>/comments", methods=["GET"])
    def get_comments_for_post(post_id: str) -> Tuple[Any, int]:
        """Retrieve all comments and nested replies for a post."""
        comments = svc.get_comments_for_post(post_id)
        return (
            jsonify(
                {
                    "status": "success",
                    "post_id": post_id,
                    "count": len(comments),
                    "data": [c.to_dict() for c in comments],
                }
            ),
            200,
        )

    @app.route("/api/comments/<int:comment_id>/replies", methods=["POST"])
    def add_reply(comment_id: int) -> Tuple[Any, int]:
        """Add a reply to an existing comment."""
        payload: Dict[str, Any] = request.get_json(silent=True) or {}
        author_id = payload.get("author_id")
        content = payload.get("content")
        post_id = payload.get("post_id")
        target_type = payload.get("target_type", "comment")

        if author_id is None or content is None:
            raise ValidationError("Payload must include both 'author_id' and 'content'.")

        reply = svc.add_reply(
            comment_id=comment_id,
            author_id=author_id,
            content=content,
            post_id=post_id,
            target_type=target_type,
        )
        return jsonify({"status": "success", "data": reply.to_dict()}), 201

    @app.route("/api/replies/<int:reply_id>/replies", methods=["POST"])
    def add_reply_to_reply(reply_id: int) -> Tuple[Any, int]:
        """Reject attempts to reply to a reply at the REST boundary."""
        raise InvalidHierarchyError(
            f"Cannot reply to reply ID {reply_id}. "
            "Discussions are strictly limited to two levels: Post -> Comment -> Reply."
        )

    @app.route("/api/comments/<int:comment_id>", methods=["GET"])
    def get_comment(comment_id: int) -> Tuple[Any, int]:
        """Retrieve a specific comment and all nested replies."""
        comment = svc.get_comment(comment_id)
        return jsonify({"status": "success", "data": comment.to_dict()}), 200

    @app.route("/api/comments/<int:comment_id>/replies", methods=["GET"])
    def get_replies_for_comment(comment_id: int) -> Tuple[Any, int]:
        """Retrieve all replies for a specific comment."""
        replies = svc.get_replies_for_comment(comment_id)
        return (
            jsonify(
                {
                    "status": "success",
                    "comment_id": comment_id,
                    "count": len(replies),
                    "data": [r.to_dict() for r in replies],
                }
            ),
            200,
        )

    @app.route("/api/stats", methods=["GET"])
    def get_stats() -> Tuple[Any, int]:
        """Get aggregate metrics."""
        return jsonify({"status": "success", "data": svc.get_stats()}), 200

    return app
