"""Historical database repair and consistency enforcement for SlotWise."""

import sqlite3
from datetime import datetime, timezone
from typing import List, Optional

from Proj_04.src.exceptions import DatabaseRepairError
from Proj_04.src.models import RepairReport


class DatabaseRepairService:
    """Production-grade in-place database repair service with dry-run rehearsal support."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def repair(self, dry_run: bool = False) -> RepairReport:
        """Inspects and repairs inconsistent historical database state in place.

        Guarantees:
        - Atomic execution: all repairs commit together or roll back completely.
        - Dry-run capability: rehearses the audit and repair without persisting mutations.
        - Complete invariant validation: verifies 100% consistency before committing.
        """
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = OFF;")  # Disable temporarily during cleanup

        report = RepairReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            dry_run=dry_run,
        )

        try:
            conn.execute("BEGIN IMMEDIATE;")

            # 1. Detect and clean orphaned reservations
            orphans = conn.execute(
                """
                SELECT reservation_id, session_id FROM reservations
                WHERE session_id NOT IN (SELECT session_id FROM sessions);
                """
            ).fetchall()
            for orphan in orphans:
                report.orphaned_reservations_cleaned += 1
                msg = f"Cleaned orphaned reservation '{orphan['reservation_id']}' referencing missing session '{orphan['session_id']}'."
                report.details.append(msg)
                if not dry_run:
                    conn.execute(
                        "DELETE FROM reservations WHERE reservation_id = ?;",
                        (orphan["reservation_id"],),
                    )

            # 2. Fix status & cancellation timestamp inconsistencies
            # 2a. Status CANCELLED but cancelled_at IS NULL
            missing_cancel_ts = conn.execute(
                """
                SELECT reservation_id, created_at FROM reservations
                WHERE status = 'CANCELLED' AND cancelled_at IS NULL;
                """
            ).fetchall()
            for r in missing_cancel_ts:
                report.corrupted_reservations_fixed += 1
                msg = f"Fixed reservation '{r['reservation_id']}': added missing cancelled_at timestamp."
                report.details.append(msg)
                if not dry_run:
                    conn.execute(
                        "UPDATE reservations SET cancelled_at = ? WHERE reservation_id = ?;",
                        (r["created_at"], r["reservation_id"]),
                    )

            # 2b. Status ACTIVE but cancelled_at IS NOT NULL
            active_with_cancel_ts = conn.execute(
                """
                SELECT reservation_id FROM reservations
                WHERE status = 'ACTIVE' AND cancelled_at IS NOT NULL;
                """
            ).fetchall()
            for r in active_with_cancel_ts:
                report.corrupted_reservations_fixed += 1
                msg = f"Fixed reservation '{r['reservation_id']}': cleared spurious cancelled_at timestamp on ACTIVE reservation."
                report.details.append(msg)
                if not dry_run:
                    conn.execute(
                        "UPDATE reservations SET cancelled_at = NULL WHERE reservation_id = ?;",
                        (r["reservation_id"],),
                    )

            # 3. Resolve duplicate active reservations per (session_id, user_id)
            duplicate_active = conn.execute(
                """
                SELECT session_id, user_id, COUNT(*) as cnt
                FROM reservations
                WHERE status = 'ACTIVE'
                GROUP BY session_id, user_id
                HAVING COUNT(*) > 1;
                """
            ).fetchall()
            for dup in duplicate_active:
                sess_id = dup["session_id"]
                u_id = dup["user_id"]
                # Fetch all active reservations for this user and session, oldest first
                records = conn.execute(
                    """
                    SELECT reservation_id, created_at FROM reservations
                    WHERE session_id = ? AND user_id = ? AND status = 'ACTIVE'
                    ORDER BY created_at ASC, reservation_id ASC;
                    """,
                    (sess_id, u_id),
                ).fetchall()
                # Keep first, cancel the rest
                for excess in records[1:]:
                    report.corrupted_reservations_fixed += 1
                    msg = f"Resolved duplicate active reservation '{excess['reservation_id']}' for user '{u_id}' on session '{sess_id}'."
                    report.details.append(msg)
                    if not dry_run:
                        conn.execute(
                            """
                            UPDATE reservations
                            SET status = 'CANCELLED', cancelled_at = ?
                            WHERE reservation_id = ?;
                            """,
                            (datetime.now(timezone.utc).isoformat(), excess["reservation_id"]),
                        )

            # 4. Resolve overbooked sessions and desynchronized capacities
            sessions = conn.execute("SELECT * FROM sessions;").fetchall()
            report.total_sessions_checked = len(sessions)

            for s in sessions:
                sess_id = s["session_id"]
                total_cap = s["total_capacity"]
                current_rem = s["remaining_capacity"]

                active_reservations = conn.execute(
                    """
                    SELECT reservation_id, created_at FROM reservations
                    WHERE session_id = ? AND status = 'ACTIVE'
                    ORDER BY created_at ASC, reservation_id ASC;
                    """,
                    (sess_id,),
                ).fetchall()

                active_count = len(active_reservations)
                session_had_repairs = False

                # 4a. Handle overbooking (active > total_capacity)
                if active_count > total_cap:
                    excess_count = active_count - total_cap
                    report.overbooked_sessions_fixed += 1
                    session_had_repairs = True

                    # Cancel excess reservations beyond total_capacity (FIFO fairness)
                    excess_records = active_reservations[total_cap:]
                    for excess in excess_records:
                        msg = f"Session '{sess_id}' overbooked: cancelled excess reservation '{excess['reservation_id']}' (FIFO fairness)."
                        report.details.append(msg)
                        if not dry_run:
                            conn.execute(
                                """
                                UPDATE reservations
                                SET status = 'CANCELLED', cancelled_at = ?
                                WHERE reservation_id = ?;
                                """,
                                (datetime.now(timezone.utc).isoformat(), excess["reservation_id"]),
                            )
                    active_count = total_cap

                # 4b. Reconcile remaining_capacity
                expected_remaining = max(0, total_cap - active_count)
                if current_rem != expected_remaining:
                    report.desynced_capacity_fixed += 1
                    session_had_repairs = True
                    msg = f"Session '{sess_id}' capacity reconciled: changed remaining_capacity from {current_rem} to {expected_remaining}."
                    report.details.append(msg)
                    if not dry_run:
                        conn.execute(
                            "UPDATE sessions SET remaining_capacity = ? WHERE session_id = ?;",
                            (expected_remaining, sess_id),
                        )

                if session_had_repairs:
                    report.sessions_repaired += 1

            # 5. Post-repair invariant verification
            if not dry_run:
                # Check 1: No negative remaining capacity
                bad_rem = conn.execute(
                    "SELECT session_id, remaining_capacity FROM sessions WHERE remaining_capacity < 0;"
                ).fetchall()
                if bad_rem:
                    raise DatabaseRepairError(f"Post-repair invariant failed: negative remaining capacity in {bad_rem}")

                # Check 2: Ground truth reconciliation
                mismatches = conn.execute(
                    """
                    SELECT s.session_id, s.total_capacity, s.remaining_capacity,
                           COUNT(r.reservation_id) as active_cnt
                    FROM sessions s
                    LEFT JOIN reservations r ON s.session_id = r.session_id AND r.status = 'ACTIVE'
                    GROUP BY s.session_id
                    HAVING s.remaining_capacity != (s.total_capacity - COUNT(r.reservation_id));
                    """
                ).fetchall()
                if mismatches:
                    raise DatabaseRepairError(
                        f"Post-repair invariant failed: ground-truth capacity mismatch in {[dict(m) for m in mismatches]}"
                    )

                # Check 3: No duplicate active reservations
                dup_check = conn.execute(
                    """
                    SELECT session_id, user_id, COUNT(*) as cnt
                    FROM reservations
                    WHERE status = 'ACTIVE'
                    GROUP BY session_id, user_id
                    HAVING COUNT(*) > 1;
                    """
                ).fetchall()
                if dup_check:
                    raise DatabaseRepairError(
                        f"Post-repair invariant failed: duplicate active reservations remain {[dict(d) for d in dup_check]}"
                    )

                # 4. Re-establish protective partial unique index if missing
                conn.execute(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_active_user_session
                    ON reservations(session_id, user_id)
                    WHERE status = 'ACTIVE';
                    """
                )

                conn.execute("COMMIT;")
            else:
                conn.execute("ROLLBACK;")

            return report

        except Exception as e:
            conn.execute("ROLLBACK;")
            if isinstance(e, DatabaseRepairError):
                raise
            raise DatabaseRepairError(f"Database repair transaction failed: {str(e)}") from e
        finally:
            conn.close()
