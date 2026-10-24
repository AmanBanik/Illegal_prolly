"""SQLite persistence repository for SlotWise Reservation Service."""

import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from Proj_04.src.exceptions import (
    AlreadyCancelledError,
    CapacityExceededError,
    DuplicateReservationError,
    ReservationNotFoundError,
    SessionNotFoundError,
    UnauthorizedCancellationError,
)
from Proj_04.src.models import (
    RepairReport,
    Reservation,
    ReservationStatus,
    Session,
    SessionCapacityReport,
)


class ReservationRepository:
    """Thread-safe SQLite repository enforcing strict ACID transaction boundaries."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._lock = threading.RLock()
        self._local = threading.local()
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(
                self.db_path,
                timeout=30.0,
                check_same_thread=False,
                isolation_level=None,  # We manage explicit transactions
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA busy_timeout = 30000;")
            self._local.conn = conn
        return self._local.conn

    def _init_schema(self) -> None:
        with self._lock:
            conn = self._get_connection()
            with conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        total_capacity INTEGER NOT NULL CHECK(total_capacity > 0),
                        remaining_capacity INTEGER NOT NULL CHECK(remaining_capacity >= 0),
                        start_time TEXT NOT NULL,
                        end_time TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS reservations (
                        reservation_id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
                        user_id TEXT NOT NULL,
                        status TEXT NOT NULL CHECK(status IN ('ACTIVE', 'CANCELLED')),
                        created_at TEXT NOT NULL,
                        cancelled_at TEXT
                    );
                    """
                )
                # Partial unique index ensuring at most one ACTIVE reservation per user per session
                conn.execute(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_active_user_session
                    ON reservations(session_id, user_id)
                    WHERE status = 'ACTIVE';
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_reservations_user
                    ON reservations(user_id);
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_reservations_session_status
                    ON reservations(session_id, status);
                    """
                )

    def create_session(
        self,
        session_id: str,
        title: str,
        total_capacity: int,
        start_time: str,
        end_time: str,
        created_at: str,
    ) -> Session:
        with self._lock:
            conn = self._get_connection()
            with conn:
                conn.execute(
                    """
                    INSERT INTO sessions (
                        session_id, title, total_capacity, remaining_capacity,
                        start_time, end_time, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        session_id,
                        title,
                        total_capacity,
                        total_capacity,  # Initially remaining == total
                        start_time,
                        end_time,
                        created_at,
                    ),
                )
            return Session(
                session_id=session_id,
                title=title,
                total_capacity=total_capacity,
                remaining_capacity=total_capacity,
                start_time=start_time,
                end_time=end_time,
                created_at=created_at,
            )

    def get_session(self, session_id: str) -> Session:
        with self._lock:
            conn = self._get_connection()
            row = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?;", (session_id,)
            ).fetchone()
            if not row:
                raise SessionNotFoundError(f"Session with ID '{session_id}' not found.")
            return Session(
                session_id=row["session_id"],
                title=row["title"],
                total_capacity=row["total_capacity"],
                remaining_capacity=row["remaining_capacity"],
                start_time=row["start_time"],
                end_time=row["end_time"],
                created_at=row["created_at"],
            )

    def list_sessions(self) -> List[Session]:
        with self._lock:
            conn = self._get_connection()
            rows = conn.execute(
                "SELECT * FROM sessions ORDER BY start_time ASC, session_id ASC;"
            ).fetchall()
            return [
                Session(
                    session_id=r["session_id"],
                    title=r["title"],
                    total_capacity=r["total_capacity"],
                    remaining_capacity=r["remaining_capacity"],
                    start_time=r["start_time"],
                    end_time=r["end_time"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]

    def make_reservation(
        self, reservation_id: str, session_id: str, user_id: str, created_at: str
    ) -> Reservation:
        """Atomically reserves a slot, ensuring zero overbooking and no duplicate reservations."""
        with self._lock:
            conn = self._get_connection()
            conn.execute("BEGIN IMMEDIATE;")
            try:
                # 1. Verify session exists
                sess_row = conn.execute(
                    "SELECT total_capacity, remaining_capacity FROM sessions WHERE session_id = ?;",
                    (session_id,),
                ).fetchone()
                if not sess_row:
                    raise SessionNotFoundError(f"Session with ID '{session_id}' not found.")

                # 2. Check if user already holds an active reservation
                existing = conn.execute(
                    """
                    SELECT reservation_id FROM reservations
                    WHERE session_id = ? AND user_id = ? AND status = 'ACTIVE';
                    """,
                    (session_id, user_id),
                ).fetchone()
                if existing:
                    raise DuplicateReservationError(
                        f"User '{user_id}' already holds an active reservation for session '{session_id}'."
                    )

                # 3. Atomic conditional decrement of remaining capacity
                cursor = conn.execute(
                    """
                    UPDATE sessions
                    SET remaining_capacity = remaining_capacity - 1
                    WHERE session_id = ? AND remaining_capacity > 0;
                    """,
                    (session_id,),
                )
                if cursor.rowcount == 0:
                    raise CapacityExceededError(
                        f"Session '{session_id}' is full. No remaining capacity."
                    )

                # 4. Insert reservation record
                conn.execute(
                    """
                    INSERT INTO reservations (
                        reservation_id, session_id, user_id, status, created_at, cancelled_at
                    ) VALUES (?, ?, ?, 'ACTIVE', ?, NULL);
                    """,
                    (reservation_id, session_id, user_id, created_at),
                )

                conn.execute("COMMIT;")
                return Reservation(
                    reservation_id=reservation_id,
                    session_id=session_id,
                    user_id=user_id,
                    status=ReservationStatus.ACTIVE,
                    created_at=created_at,
                    cancelled_at=None,
                )
            except Exception:
                conn.execute("ROLLBACK;")
                raise

    def cancel_reservation(
        self, reservation_id: str, user_id: str, cancelled_at: str
    ) -> Reservation:
        """Atomically cancels an active reservation and restores capacity."""
        with self._lock:
            conn = self._get_connection()
            conn.execute("BEGIN IMMEDIATE;")
            try:
                # 1. Fetch reservation
                row = conn.execute(
                    "SELECT * FROM reservations WHERE reservation_id = ?;",
                    (reservation_id,),
                ).fetchone()
                if not row:
                    raise ReservationNotFoundError(
                        f"Reservation with ID '{reservation_id}' not found."
                    )

                # 2. Verify ownership
                if row["user_id"] != user_id:
                    raise UnauthorizedCancellationError(
                        f"User '{user_id}' is not authorized to cancel reservation '{reservation_id}'."
                    )

                # 3. Check already cancelled
                if row["status"] == ReservationStatus.CANCELLED.value:
                    raise AlreadyCancelledError(
                        f"Reservation '{reservation_id}' is already cancelled."
                    )

                # 4. Update reservation status to CANCELLED
                conn.execute(
                    """
                    UPDATE reservations
                    SET status = 'CANCELLED', cancelled_at = ?
                    WHERE reservation_id = ?;
                    """,
                    (cancelled_at, reservation_id),
                )

                # 5. Restore session remaining capacity (capped at total_capacity)
                conn.execute(
                    """
                    UPDATE sessions
                    SET remaining_capacity = MIN(total_capacity, remaining_capacity + 1)
                    WHERE session_id = ?;
                    """,
                    (row["session_id"],),
                )

                conn.execute("COMMIT;")
                return Reservation(
                    reservation_id=row["reservation_id"],
                    session_id=row["session_id"],
                    user_id=row["user_id"],
                    status=ReservationStatus.CANCELLED,
                    created_at=row["created_at"],
                    cancelled_at=cancelled_at,
                )
            except Exception:
                conn.execute("ROLLBACK;")
                raise

    def get_reservation(self, reservation_id: str) -> Reservation:
        with self._lock:
            conn = self._get_connection()
            row = conn.execute(
                "SELECT * FROM reservations WHERE reservation_id = ?;",
                (reservation_id,),
            ).fetchone()
            if not row:
                raise ReservationNotFoundError(
                    f"Reservation with ID '{reservation_id}' not found."
                )
            return Reservation(
                reservation_id=row["reservation_id"],
                session_id=row["session_id"],
                user_id=row["user_id"],
                status=ReservationStatus(row["status"]),
                created_at=row["created_at"],
                cancelled_at=row["cancelled_at"],
            )

    def list_user_reservations(self, user_id: str) -> List[Reservation]:
        with self._lock:
            conn = self._get_connection()
            rows = conn.execute(
                """
                SELECT * FROM reservations
                WHERE user_id = ?
                ORDER BY created_at DESC, reservation_id ASC;
                """,
                (user_id,),
            ).fetchall()
            return [
                Reservation(
                    reservation_id=r["reservation_id"],
                    session_id=r["session_id"],
                    user_id=r["user_id"],
                    status=ReservationStatus(r["status"]),
                    created_at=r["created_at"],
                    cancelled_at=r["cancelled_at"],
                )
                for r in rows
            ]

    def get_session_capacity_report(self, session_id: str) -> SessionCapacityReport:
        """Calculates ground-truth capacity by aggregating active reservations."""
        with self._lock:
            conn = self._get_connection()
            sess = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?;", (session_id,)
            ).fetchone()
            if not sess:
                raise SessionNotFoundError(f"Session with ID '{session_id}' not found.")

            counts = conn.execute(
                """
                SELECT
                    SUM(CASE WHEN status = 'ACTIVE' THEN 1 ELSE 0 END) AS active_cnt,
                    SUM(CASE WHEN status = 'CANCELLED' THEN 1 ELSE 0 END) AS cancelled_cnt
                FROM reservations
                WHERE session_id = ?;
                """,
                (session_id,),
            ).fetchone()

            active_cnt = counts["active_cnt"] or 0
            cancelled_cnt = counts["cancelled_cnt"] or 0
            remaining = sess["remaining_capacity"]
            total = sess["total_capacity"]

            # Ground truth consistency: remaining must equal total - active
            is_consistent = remaining == (total - active_cnt)

            return SessionCapacityReport(
                session_id=sess["session_id"],
                title=sess["title"],
                total_capacity=total,
                active_reservations=active_cnt,
                cancelled_reservations=cancelled_cnt,
                remaining_capacity=remaining,
                is_consistent=is_consistent,
            )

    def close(self) -> None:
        with self._lock:
            if hasattr(self._local, "conn") and self._local.conn is not None:
                self._local.conn.close()
                self._local.conn = None
