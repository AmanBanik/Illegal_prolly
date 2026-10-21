from dataclasses import asdict
from typing import Optional
from flask import Flask, jsonify, redirect, request
from .exceptions import ShortenerError
from .models import CreateLinkRequest
from .repository import LinkRepository
from .service import UrlShortenerService


def create_app(
    service: Optional[UrlShortenerService] = None,
    db_path: str = ":memory:",
) -> Flask:
    """Factory creating and configuring the Flask URL shortener application."""
    app = Flask(__name__)

    if service is None:
        repo = LinkRepository(db_path=db_path)
        service = UrlShortenerService(repository=repo)

    app.config["SHORTENER_SERVICE"] = service

    def get_service() -> UrlShortenerService:
        return app.config["SHORTENER_SERVICE"]

    # Global Error Handler
    @app.errorhandler(ShortenerError)
    def handle_shortener_error(err: ShortenerError):
        return (
            jsonify({"error": err.message, "status_code": err.status_code}),
            err.status_code,
        )

    @app.errorhandler(400)
    def handle_bad_request(err):
        return jsonify({"error": "Bad Request", "status_code": 400}), 400

    @app.errorhandler(404)
    def handle_not_found(err):
        return jsonify({"error": "Not Found", "status_code": 404}), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(err):
        return jsonify({"error": "Method Not Allowed", "status_code": 405}), 405

    # 1. Create Short Link
    @app.route("/api/links", methods=["POST"])
    def create_link():
        payload = request.get_json(silent=True)
        if not payload or not isinstance(payload, dict):
            return jsonify({"error": "Invalid JSON body", "status_code": 400}), 400

        user_id = request.headers.get("X-User-ID", payload.get("user_id", "anonymous"))
        req_obj = CreateLinkRequest(
            original_url=payload.get("original_url", ""),
            user_id=user_id,
            custom_code=payload.get("custom_code"),
            ttl_seconds=payload.get("ttl_seconds"),
        )
        base_url = request.host_url.rstrip("/")
        metadata = get_service().create_short_link(req_obj, base_url=base_url)
        return jsonify(asdict(metadata)), 201

    # 2. Redirect to Original URL (Hit Counting)
    @app.route("/<short_code>", methods=["GET"])
    def redirect_link(short_code: str):
        target_url = get_service().get_destination_and_record_hit(short_code)
        return redirect(target_url, code=302)

    # 3. Retrieve Link Metadata
    @app.route("/api/links/<short_code>", methods=["GET"])
    def get_metadata(short_code: str):
        base_url = request.host_url.rstrip("/")
        meta = get_service().get_link_metadata(short_code, base_url=base_url)
        return jsonify(asdict(meta)), 200

    # 4. Delete Short Link (Ownership Check)
    @app.route("/api/links/<short_code>", methods=["DELETE"])
    def delete_link(short_code: str):
        user_id = request.headers.get("X-User-ID")
        if not user_id:
            payload = request.get_json(silent=True) or {}
            user_id = payload.get("user_id")

        if not user_id:
            return jsonify({"error": "X-User-ID header or user_id required", "status_code": 403}), 403

        get_service().delete_link(short_code, requesting_user_id=user_id)
        return "", 204

    # 5. Aggregate Usage Statistics
    @app.route("/api/stats", methods=["GET"])
    def get_stats():
        user_id = request.args.get("user_id")
        stats = get_service().get_aggregate_stats(user_id=user_id)
        return jsonify(asdict(stats)), 200

    return app
