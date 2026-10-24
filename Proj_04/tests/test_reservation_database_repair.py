"""Tests for in-place historical database audit, rehearsal (dry-run), and repair."""

import sqlite3
import pytest
from Proj_04.src.models import ReservationStatus
from Proj_04.src.repair import DatabaseRepairService


def test_dry_run_rehearsal_does_not_modify_database(temp_db_path, service):
    # Setup corrupted session directly in database
    conn = sqlite3.connect(temp_db_path)
    with conn:
        conn.execute(
            """
            INSERT INTO sessions (session_id, title, total_capacity, remaining_capacity, start_time, end_time, created_at)
            VALUES ('sess_corrupt', 'Corrupt Session', 10, 999, '2026-11-01T10:00:00Z', '2026-11-01T12:00:00Z', '2026-10-01T00:00:00Z');
            """
        )
        conn.execute(
            """
            INSERT INTO reservations (reservation_id, session_id, user_id, status, created_at, cancelled_at)
            VALUES ('res_1', 'sess_corrupt', 'u1', 'ACTIVE', '2026-10-01T00:00:00Z', NULL);
            """
        )
    conn.close()

    # Dry-run repair
    repairer = DatabaseRepairService(temp_db_path)
    report = repairer.repair(dry_run=True)

    assert report.dry_run is True
    assert report.desynced_capacity_fixed == 1
    assert report.sessions_repaired == 1

    # In database, remaining_capacity must STILL be 999
    conn = sqlite3.connect(temp_db_path)
    row = conn.execute("SELECT remaining_capacity FROM sessions WHERE session_id = 'sess_corrupt';").fetchone()
    conn.close()
    assert row[0] == 999


def test_in_place_database_repair_reconciles_desynced_capacity(temp_db_path, service):
    conn = sqlite3.connect(temp_db_path)
    with conn:
        conn.execute(
            """
            INSERT INTO sessions (session_id, title, total_capacity, remaining_capacity, start_time, end_time, created_at)
            VALUES ('sess_desync', 'Desynced Session', 10, 2, '2026-11-01T10:00:00Z', '2026-11-01T12:00:00Z', '2026-10-01T00:00:00Z');
            """
        )
        # Only 1 active reservation, but remaining_capacity was falsely 2 instead of 9!
        conn.execute(
            """
            INSERT INTO reservations (reservation_id, session_id, user_id, status, created_at, cancelled_at)
            VALUES ('res_active_1', 'sess_desync', 'u1', 'ACTIVE', '2026-10-01T00:00:00Z', NULL);
            """
        )
    conn.close()

    repairer = DatabaseRepairService(temp_db_path)
    report = repairer.repair(dry_run=False)

    assert report.dry_run is False
    assert report.desynced_capacity_fixed == 1

    # Verify repaired session
    sess = service.get_session("sess_desync")
    assert sess.remaining_capacity == 9

    cap_report = service.get_session_capacity("sess_desync")
    assert cap_report.is_consistent is True
    assert cap_report.remaining_capacity == 9
    assert cap_report.active_reservations == 1


def test_in_place_repair_resolves_overbooking_with_fifo_fairness(temp_db_path, service):
    """Verifies that an overbooked session keeps the earliest reservations and cancels excess."""
    conn = sqlite3.connect(temp_db_path)
    with conn:
        conn.execute(
            """
            INSERT INTO sessions (session_id, title, total_capacity, remaining_capacity, start_time, end_time, created_at)
            VALUES ('sess_overbooked', 'Overbooked Workshop', 2, 0, '2026-11-01T10:00:00Z', '2026-11-01T12:00:00Z', '2026-10-01T00:00:00Z');
            """
        )
        # 4 active reservations when capacity is only 2
        for i in range(1, 5):
            conn.execute(
                f"""
                INSERT INTO reservations (reservation_id, session_id, user_id, status, created_at, cancelled_at)
                VALUES ('res_over_{i}', 'sess_overbooked', 'user_{i}', 'ACTIVE', '2026-10-0{i}T00:00:00Z', NULL);
                """
            )
    conn.close()

    repairer = DatabaseRepairService(temp_db_path)
    report = repairer.repair(dry_run=False)

    assert report.overbooked_sessions_fixed == 1

    # Check that first 2 remain ACTIVE, last 2 are CANCELLED
    r1 = service.get_reservation("res_over_1")
    r2 = service.get_reservation("res_over_2")
    r3 = service.get_reservation("res_over_3")
    r4 = service.get_reservation("res_over_4")

    assert r1.status == ReservationStatus.ACTIVE
    assert r2.status == ReservationStatus.ACTIVE
    assert r3.status == ReservationStatus.CANCELLED
    assert r4.status == ReservationStatus.CANCELLED

    # Check capacity report is now 100% consistent
    cap_report = service.get_session_capacity("sess_overbooked")
    assert cap_report.total_capacity == 2
    assert cap_report.active_reservations == 2
    assert cap_report.cancelled_reservations == 2
    assert cap_report.remaining_capacity == 0
    assert cap_report.is_consistent is True


def test_in_place_repair_cleans_orphaned_and_duplicate_active_reservations(temp_db_path, service):
    conn = sqlite3.connect(temp_db_path)
    with conn:
        # Drop unique index temporarily to simulate unconstrained legacy state
        conn.execute("DROP INDEX IF EXISTS idx_active_user_session;")
        conn.execute(
            """
            INSERT INTO sessions (session_id, title, total_capacity, remaining_capacity, start_time, end_time, created_at)
            VALUES ('sess_dups', 'Dups Session', 5, 5, '2026-11-01T10:00:00Z', '2026-11-01T12:00:00Z', '2026-10-01T00:00:00Z');
            """
        )
        # Duplicate active reservations for same user
        conn.execute(
            """
            INSERT INTO reservations (reservation_id, session_id, user_id, status, created_at, cancelled_at)
            VALUES ('res_dup_1', 'sess_dups', 'user_same', 'ACTIVE', '2026-10-01T00:00:00Z', NULL);
            """
        )
        conn.execute(
            """
            INSERT INTO reservations (reservation_id, session_id, user_id, status, created_at, cancelled_at)
            VALUES ('res_dup_2', 'sess_dups', 'user_same', 'ACTIVE', '2026-10-02T00:00:00Z', NULL);
            """
        )
        # Orphaned reservation pointing to missing session
        conn.execute(
            """
            INSERT INTO reservations (reservation_id, session_id, user_id, status, created_at, cancelled_at)
            VALUES ('res_orphan', 'sess_ghost', 'user_ghost', 'ACTIVE', '2026-10-01T00:00:00Z', NULL);
            """
        )
        # Corrupted status: CANCELLED with NULL cancelled_at
        conn.execute(
            """
            INSERT INTO reservations (reservation_id, session_id, user_id, status, created_at, cancelled_at)
            VALUES ('res_corrupt_cancel', 'sess_dups', 'user_canc', 'CANCELLED', '2026-10-01T00:00:00Z', NULL);
            """
        )
    conn.close()

    repairer = DatabaseRepairService(temp_db_path)
    report = repairer.repair(dry_run=False)

    assert report.orphaned_reservations_cleaned == 1
    assert report.corrupted_reservations_fixed >= 2

    # Verify duplicate was resolved
    r_dup1 = service.get_reservation("res_dup_1")
    r_dup2 = service.get_reservation("res_dup_2")
    assert r_dup1.status == ReservationStatus.ACTIVE
    assert r_dup2.status == ReservationStatus.CANCELLED

    # Verify missing cancel timestamp fixed
    r_fixed = service.get_reservation("res_corrupt_cancel")
    assert r_fixed.cancelled_at is not None

    # Verify capacity consistent
    cap_report = service.get_session_capacity("sess_dups")
    assert cap_report.is_consistent is True
    assert cap_report.remaining_capacity == 4  # 5 - 1 active
