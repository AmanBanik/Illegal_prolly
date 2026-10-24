"""Application service layer for SlotWise Reservation Service."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from Proj_04.src.exceptions import ValidationError
from Proj_04.src.models import (
    RepairReport,
    Reservation,
    Session,
    SessionCapacityReport,
)
from Proj_04.src.repair import DatabaseRepairService
from Proj_04.src.repository import ReservationRepository


class ReservationService:
    """Orchestrates reservation business logic, validation, and database operations."""

    def __init__(self, repository: Optional[ReservationRepository] = None, db_path: str = ":memory:"):
        self.db_path = db_path
        self.repository = repository or ReservationRepository(db_path=db_path)

    def _validate_string(self, value: str, field_name: str) -> str:
        if isinstance(value, bool) or not isinstance(value, str):
            raise ValidationError(f"Field '{field_name}' must be a string, got {type(value).__name__}.")
        val_clean = value.strip()
        if not val_clean:
            raise ValidationError(f"Field '{field_name}' cannot be empty or whitespace.")
        return val_clean

    def _validate_capacity(self, capacity: int) -> int:
        if isinstance(capacity, bool) or not isinstance(capacity, int):
            raise ValidationError(f"total_capacity must be an integer, got {type(capacity).__name__}.")
        if capacity <= 0:
            raise ValidationError(f"total_capacity must be strictly positive (> 0), got {capacity}.")
        return capacity

    def _validate_timestamps(self, start_time: str, end_time: str) -> None:
        try:
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        except Exception as e:
            raise ValidationError(f"Invalid start_time format '{start_time}': must be ISO 8601.") from e

        try:
            end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        except Exception as e:
            raise ValidationError(f"Invalid end_time format '{end_time}': must be ISO 8601.") from e

        if end_dt <= start_dt:
            raise ValidationError(f"end_time ({end_time}) must be strictly after start_time ({start_time}).")

    def create_session(
        self,
        title: str,
        total_capacity: int,
        start_time: str,
        end_time: str,
        session_id: Optional[str] = None,
    ) -> Session:
        clean_title = self._validate_string(title, "title")
        clean_capacity = self._validate_capacity(total_capacity)
        clean_start = self._validate_string(start_time, "start_time")
        clean_end = self._validate_string(end_time, "end_time")
        self._validate_timestamps(clean_start, clean_end)

        sess_id = (
            self._validate_string(session_id, "session_id")
            if session_id
            else f"sess_{uuid.uuid4().hex[:12]}"
        )
        created_at = datetime.now(timezone.utc).isoformat()

        return self.repository.create_session(
            session_id=sess_id,
            title=clean_title,
            total_capacity=clean_capacity,
            start_time=clean_start,
            end_time=clean_end,
            created_at=created_at,
        )

    def get_session(self, session_id: str) -> Session:
        clean_id = self._validate_string(session_id, "session_id")
        return self.repository.get_session(clean_id)

    def list_sessions(self) -> List[Session]:
        return self.repository.list_sessions()

    def make_reservation(
        self, session_id: str, user_id: str, reservation_id: Optional[str] = None
    ) -> Reservation:
        clean_session_id = self._validate_string(session_id, "session_id")
        clean_user_id = self._validate_string(user_id, "user_id")
        res_id = (
            self._validate_string(reservation_id, "reservation_id")
            if reservation_id
            else f"res_{uuid.uuid4().hex[:12]}"
        )
        created_at = datetime.now(timezone.utc).isoformat()

        return self.repository.make_reservation(
            reservation_id=res_id,
            session_id=clean_session_id,
            user_id=clean_user_id,
            created_at=created_at,
        )

    def cancel_reservation(self, reservation_id: str, user_id: str) -> Reservation:
        clean_res_id = self._validate_string(reservation_id, "reservation_id")
        clean_user_id = self._validate_string(user_id, "user_id")
        cancelled_at = datetime.now(timezone.utc).isoformat()

        return self.repository.cancel_reservation(
            reservation_id=clean_res_id,
            user_id=clean_user_id,
            cancelled_at=cancelled_at,
        )

    def get_reservation(self, reservation_id: str) -> Reservation:
        clean_res_id = self._validate_string(reservation_id, "reservation_id")
        return self.repository.get_reservation(clean_res_id)

    def list_user_reservations(self, user_id: str) -> List[Reservation]:
        clean_user_id = self._validate_string(user_id, "user_id")
        return self.repository.list_user_reservations(clean_user_id)

    def get_session_capacity(self, session_id: str) -> SessionCapacityReport:
        clean_session_id = self._validate_string(session_id, "session_id")
        return self.repository.get_session_capacity_report(clean_session_id)

    def repair_database(self, dry_run: bool = False) -> RepairReport:
        """Executes historical data repair on the active database."""
        repair_service = DatabaseRepairService(self.repository.db_path)
        return repair_service.repair(dry_run=dry_run)

    def close(self) -> None:
        self.repository.close()
