"""Tests for Flask REST API endpoints and HTTP error mappings."""

def test_api_create_and_list_sessions(client):
    res = client.post(
        "/api/sessions",
        json={
            "title": "API Workshop",
            "total_capacity": 8,
            "start_time": "2026-11-10T10:00:00Z",
            "end_time": "2026-11-10T12:00:00Z",
        },
    )
    assert res.status_code == 201
    data = res.get_json()
    assert data["title"] == "API Workshop"
    assert data["total_capacity"] == 8
    assert data["remaining_capacity"] == 8
    sess_id = data["session_id"]

    # List
    list_res = client.get("/api/sessions")
    assert list_res.status_code == 200
    sessions = list_res.get_json()
    assert len(sessions) >= 1
    assert any(s["session_id"] == sess_id for s in sessions)


def test_api_get_session_not_found(client):
    res = client.get("/api/sessions/nonexistent")
    assert res.status_code == 404
    data = res.get_json()
    assert data["error"] == "SESSION_NOT_FOUND"


def test_api_get_session_capacity_report(client):
    res = client.post(
        "/api/sessions",
        json={
            "title": "Capacity Check",
            "total_capacity": 5,
            "start_time": "2026-11-10T10:00:00Z",
            "end_time": "2026-11-10T12:00:00Z",
        },
    )
    sess_id = res.get_json()["session_id"]

    cap_res = client.get(f"/api/sessions/{sess_id}/capacity")
    assert cap_res.status_code == 200
    report = cap_res.get_json()
    assert report["total_capacity"] == 5
    assert report["remaining_capacity"] == 5
    assert report["active_reservations"] == 0
    assert report["is_consistent"] is True


def test_api_reserve_and_capacity_exceeded(client):
    # Session with capacity 1
    res = client.post(
        "/api/sessions",
        json={
            "title": "Solo Seat",
            "total_capacity": 1,
            "start_time": "2026-11-10T10:00:00Z",
            "end_time": "2026-11-10T12:00:00Z",
        },
    )
    sess_id = res.get_json()["session_id"]

    # Book 1
    r1 = client.post(f"/api/sessions/{sess_id}/reserve", json={"user_id": "u1"})
    assert r1.status_code == 201

    # Duplicate book attempt by same user
    r_dup = client.post(f"/api/sessions/{sess_id}/reserve", json={"user_id": "u1"})
    assert r_dup.status_code == 409
    assert r_dup.get_json()["error"] == "DUPLICATE_RESERVATION"

    # Second user book attempt -> capacity exceeded
    r2 = client.post(f"/api/sessions/{sess_id}/reserve", json={"user_id": "u2"})
    assert r2.status_code == 409
    assert r2.get_json()["error"] == "CAPACITY_EXCEEDED"


def test_api_cancel_and_unauthorized(client):
    res = client.post(
        "/api/sessions",
        json={
            "title": "Cancel Test",
            "total_capacity": 5,
            "start_time": "2026-11-10T10:00:00Z",
            "end_time": "2026-11-10T12:00:00Z",
        },
    )
    sess_id = res.get_json()["session_id"]
    book_res = client.post(f"/api/sessions/{sess_id}/reserve", json={"user_id": "user_owner"})
    res_id = book_res.get_json()["reservation_id"]

    # Unauthorized cancel
    unauth = client.post(f"/api/reservations/{res_id}/cancel", json={"user_id": "user_hacker"})
    assert unauth.status_code == 403
    assert unauth.get_json()["error"] == "UNAUTHORIZED_CANCELLATION"

    # Authorized cancel
    auth = client.post(f"/api/reservations/{res_id}/cancel", json={"user_id": "user_owner"})
    assert auth.status_code == 200
    assert auth.get_json()["status"] == "CANCELLED"

    # Second cancel -> 409 Already Cancelled
    re_cancel = client.post(f"/api/reservations/{res_id}/cancel", json={"user_id": "user_owner"})
    assert re_cancel.status_code == 409
    assert re_cancel.get_json()["error"] == "ALREADY_CANCELLED"


def test_api_admin_repair_endpoint(client):
    res = client.post("/api/admin/repair", json={"dry_run": True})
    assert res.status_code == 200
    report = res.get_json()
    assert report["dry_run"] is True
    assert "timestamp" in report
