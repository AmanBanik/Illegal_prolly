"""Flask REST API adapter for SlotWise Reservation Service."""

from typing import Optional

from flask import Flask, jsonify, request

from Proj_04.src.exceptions import (
    AlreadyCancelledError,
    CapacityExceededError,
    DatabaseRepairError,
    DuplicateReservationError,
    ReservationNotFoundError,
    SessionNotFoundError,
    UnauthorizedCancellationError,
    ValidationError,
)
from Proj_04.src.service import ReservationService


def create_app(service: Optional[ReservationService] = None) -> Flask:
    app = Flask(__name__)
    svc = service or ReservationService(db_path=":memory:")

    @app.errorhandler(ValidationError)
    def handle_validation_error(e: ValidationError):
        return jsonify({"error": "VALIDATION_ERROR", "message": str(e)}), 400

    @app.errorhandler(SessionNotFoundError)
    def handle_session_not_found(e: SessionNotFoundError):
        return jsonify({"error": "SESSION_NOT_FOUND", "message": str(e)}), 404

    @app.errorhandler(ReservationNotFoundError)
    def handle_reservation_not_found(e: ReservationNotFoundError):
        return jsonify({"error": "RESERVATION_NOT_FOUND", "message": str(e)}), 404

    @app.errorhandler(CapacityExceededError)
    def handle_capacity_exceeded(e: CapacityExceededError):
        return jsonify({"error": "CAPACITY_EXCEEDED", "message": str(e)}), 409

    @app.errorhandler(DuplicateReservationError)
    def handle_duplicate_reservation(e: DuplicateReservationError):
        return jsonify({"error": "DUPLICATE_RESERVATION", "message": str(e)}), 409

    @app.errorhandler(UnauthorizedCancellationError)
    def handle_unauthorized_cancellation(e: UnauthorizedCancellationError):
        return jsonify({"error": "UNAUTHORIZED_CANCELLATION", "message": str(e)}), 403

    @app.errorhandler(AlreadyCancelledError)
    def handle_already_cancelled(e: AlreadyCancelledError):
        return jsonify({"error": "ALREADY_CANCELLED", "message": str(e)}), 409

    @app.errorhandler(DatabaseRepairError)
    def handle_repair_error(e: DatabaseRepairError):
        return jsonify({"error": "DATABASE_REPAIR_ERROR", "message": str(e)}), 500

    @app.route("/api/sessions", methods=["POST"])
    def create_session():
        data = request.get_json(force=True, silent=True) or {}
        session = svc.create_session(
            title=data.get("title"),
            total_capacity=data.get("total_capacity"),
            start_time=data.get("start_time"),
            end_time=data.get("end_time"),
            session_id=data.get("session_id"),
        )
        return jsonify(session.to_dict()), 201

    @app.route("/api/sessions", methods=["GET"])
    def list_sessions():
        sessions = svc.list_sessions()
        return jsonify([s.to_dict() for s in sessions]), 200

    @app.route("/api/sessions/<session_id>", methods=["GET"])
    def get_session(session_id: str):
        session = svc.get_session(session_id)
        return jsonify(session.to_dict()), 200

    @app.route("/api/sessions/<session_id>/capacity", methods=["GET"])
    def get_session_capacity(session_id: str):
        report = svc.get_session_capacity(session_id)
        return jsonify(report.to_dict()), 200

    @app.route("/api/sessions/<session_id>/reserve", methods=["POST"])
    def make_reservation(session_id: str):
        data = request.get_json(force=True, silent=True) or {}
        user_id = data.get("user_id")
        reservation_id = data.get("reservation_id")
        reservation = svc.make_reservation(
            session_id=session_id,
            user_id=user_id,
            reservation_id=reservation_id,
        )
        return jsonify(reservation.to_dict()), 201

    @app.route("/api/reservations/<reservation_id>/cancel", methods=["POST"])
    def cancel_reservation(reservation_id: str):
        data = request.get_json(force=True, silent=True) or {}
        user_id = data.get("user_id")
        reservation = svc.cancel_reservation(
            reservation_id=reservation_id,
            user_id=user_id,
        )
        return jsonify(reservation.to_dict()), 200

    @app.route("/api/reservations/<reservation_id>", methods=["GET"])
    def get_reservation(reservation_id: str):
        res = svc.get_reservation(reservation_id)
        return jsonify(res.to_dict()), 200

    @app.route("/api/users/<user_id>/reservations", methods=["GET"])
    def list_user_reservations(user_id: str):
        reservations = svc.list_user_reservations(user_id)
        return jsonify([r.to_dict() for r in reservations]), 200

    @app.route("/api/admin/repair", methods=["POST"])
    def repair_database():
        data = request.get_json(force=True, silent=True) or {}
        dry_run = data.get("dry_run", False)
        report = svc.repair_database(dry_run=dry_run)
        return jsonify(report.to_dict()), 200

    return app
