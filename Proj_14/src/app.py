from typing import Optional
from flask import Flask, jsonify, request
from .exceptions import UnauthorizedError, ValidationError, WatchlistServiceError
from .service import ScreenShelf


def create_app(service: Optional[ScreenShelf] = None, db_path: str = ":memory:") -> Flask:
    """Factory creating the Flask REST API application for ScreenShelf."""
    app = Flask(__name__)
    shelf = service or ScreenShelf(db_path=db_path)
    app.config["WATCHLIST_SERVICE"] = shelf

    def _get_user_id() -> str:
        user_id = request.headers.get("X-User-ID", "").strip()
        if not user_id:
            raise UnauthorizedError("Missing or empty 'X-User-ID' authentication header", status_code=401)
        return user_id

    @app.errorhandler(WatchlistServiceError)
    def handle_service_error(err: WatchlistServiceError):
        return jsonify({"error": err.message}), err.status_code

    @app.errorhandler(400)
    def handle_bad_request(err):
        return jsonify({"error": "Bad request"}), 400

    @app.errorhandler(404)
    def handle_not_found(err):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(500)
    def handle_internal_error(err):
        return jsonify({"error": "Internal server error"}), 500

    @app.route("/api/watchlists", methods=["POST"])
    def create_watchlist():
        user_id = _get_user_id()
        data = request.get_json(silent=True) or {}
        name = data.get("name")
        description = data.get("description")

        watchlist = shelf.create_watchlist(user_id=user_id, name=name, description=description)
        return jsonify(watchlist.to_dict()), 201

    @app.route("/api/watchlists", methods=["GET"])
    def list_watchlists():
        user_id = _get_user_id()
        watchlists = shelf.list_watchlists(user_id=user_id)
        return jsonify([w.to_dict() for w in watchlists]), 200

    @app.route("/api/watchlists/<int:watchlist_id>", methods=["GET"])
    def get_watchlist(watchlist_id: int):
        user_id = _get_user_id()
        watchlist = shelf.get_watchlist(watchlist_id=watchlist_id, user_id=user_id)
        return jsonify(watchlist.to_dict()), 200

    @app.route("/api/watchlists/<int:watchlist_id>", methods=["PATCH", "PUT"])
    def rename_watchlist(watchlist_id: int):
        user_id = _get_user_id()
        data = request.get_json(silent=True) or {}
        new_name = data.get("name")
        if not new_name:
            raise ValidationError("Field 'name' is required for renaming")

        updated = shelf.rename_watchlist(watchlist_id=watchlist_id, user_id=user_id, new_name=new_name)
        return jsonify(updated.to_dict()), 200

    @app.route("/api/watchlists/<int:watchlist_id>", methods=["DELETE"])
    def delete_watchlist(watchlist_id: int):
        user_id = _get_user_id()
        shelf.delete_watchlist(watchlist_id=watchlist_id, user_id=user_id)
        return jsonify({"message": f"Watchlist #{watchlist_id} deleted successfully"}), 200

    @app.route("/api/watchlists/<int:watchlist_id>/movies", methods=["POST"])
    def add_movie_to_watchlist(watchlist_id: int):
        user_id = _get_user_id()
        data = request.get_json(silent=True) or {}
        movie_id = data.get("movie_id")
        title = data.get("title")
        metadata = data.get("metadata")

        movie = shelf.add_movie(
            watchlist_id=watchlist_id,
            user_id=user_id,
            movie_id=movie_id,
            title=title,
            metadata=metadata,
        )
        return jsonify(movie.to_dict()), 201

    @app.route("/api/watchlists/<int:watchlist_id>/movies/<string:movie_id>", methods=["DELETE"])
    def remove_movie_from_watchlist(watchlist_id: int, movie_id: str):
        user_id = _get_user_id()
        shelf.remove_movie(watchlist_id=watchlist_id, user_id=user_id, movie_id=movie_id)
        return jsonify({"message": f"Movie '{movie_id}' removed from watchlist #{watchlist_id}"}), 200

    return app
