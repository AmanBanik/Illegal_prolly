"""Tests for Flask REST API adapter, HTTP headers, and error mappings."""

def test_api_create_and_get_project(client):
    # Missing auth header
    res_no_auth = client.post(
        "/api/projects",
        json={"project_id": "p_web", "name": "Web Dashboard"},
    )
    assert res_no_auth.status_code == 400
    assert res_no_auth.get_json()["error"] == "VALIDATION_ERROR"

    # Valid creation
    res = client.post(
        "/api/projects",
        headers={"X-User-ID": "admin_alice"},
        json={"project_id": "p_web", "name": "Web Dashboard"},
    )
    assert res.status_code == 201
    assert res.get_json()["project_id"] == "p_web"

    # Get project
    get_res = client.get("/api/projects/p_web", headers={"X-User-ID": "admin_alice"})
    assert get_res.status_code == 200
    assert get_res.get_json()["name"] == "Web Dashboard"


def test_api_add_member(client):
    client.post(
        "/api/projects",
        headers={"X-User-ID": "admin_alice"},
        json={"project_id": "p_auth_test", "name": "Auth Test"},
    )

    # Admin adds member
    res = client.post(
        "/api/projects/p_auth_test/members",
        headers={"X-User-ID": "admin_alice"},
        json={"user_id": "developer_dan", "role": "MEMBER"},
    )
    assert res.status_code == 200
    assert res.get_json()["status"] == "MEMBER_ADDED"

    # Non-admin trying to add member -> 403 Forbidden
    res_unauth = client.post(
        "/api/projects/p_auth_test/members",
        headers={"X-User-ID": "developer_dan"},
        json={"user_id": "outsider", "role": "VIEWER"},
    )
    assert res_unauth.status_code == 403
    assert res_unauth.get_json()["error"] == "AUTHORIZATION_ERROR"


def test_api_create_issue_with_idempotency_headers(client):
    client.post(
        "/api/projects",
        headers={"X-User-ID": "admin_alice"},
        json={"project_id": "p_idem", "name": "Idempotency Test"},
    )

    # 1. Create issue with Idempotency-Key
    res1 = client.post(
        "/api/projects/p_idem/issues",
        headers={"X-User-ID": "admin_alice", "Idempotency-Key": "req_key_999"},
        json={"title": "Fix Memory Leak", "description": "Unbounded cache growth."},
    )
    assert res1.status_code == 201
    issue_data = res1.get_json()
    assert issue_data["version"] == 1
    issue_id = issue_data["issue_id"]

    # 2. Retrying identical request returns same issue
    res2 = client.post(
        "/api/projects/p_idem/issues",
        headers={"X-User-ID": "admin_alice", "Idempotency-Key": "req_key_999"},
        json={"title": "Fix Memory Leak", "description": "Unbounded cache growth."},
    )
    assert res2.status_code == 201
    assert res2.get_json()["issue_id"] == issue_id

    # 3. Reusing key with different title returns 409 Conflict
    res3 = client.post(
        "/api/projects/p_idem/issues",
        headers={"X-User-ID": "admin_alice", "Idempotency-Key": "req_key_999"},
        json={"title": "Different Title", "description": "Unbounded cache growth."},
    )
    assert res3.status_code == 409
    assert res3.get_json()["error"] == "IDEMPOTENCY_CONFLICT"


def test_api_update_issue_with_if_match_header(client):
    client.post(
        "/api/projects",
        headers={"X-User-ID": "admin_alice"},
        json={"project_id": "p_occ", "name": "OCC Test"},
    )
    create_res = client.post(
        "/api/projects/p_occ/issues",
        headers={"X-User-ID": "admin_alice"},
        json={"title": "Original OCC", "description": "Desc"},
    )
    issue_id = create_res.get_json()["issue_id"]

    # Update with valid If-Match: "1"
    u1 = client.put(
        f"/api/projects/p_occ/issues/{issue_id}",
        headers={"X-User-ID": "admin_alice", "If-Match": '"1"'},
        json={"title": "Updated OCC 1"},
    )
    assert u1.status_code == 200
    assert u1.get_json()["version"] == 2
    assert u1.get_json()["title"] == "Updated OCC 1"

    # Stale If-Match: "1" -> 409 Conflict
    u_stale = client.put(
        f"/api/projects/p_occ/issues/{issue_id}",
        headers={"X-User-ID": "admin_alice", "If-Match": '"1"'},
        json={"title": "Stale Attempt"},
    )
    assert u_stale.status_code == 409
    assert u_stale.get_json()["error"] == "VERSION_CONFLICT"

    # Valid If-Match: "2" -> 200 OK
    u2 = client.put(
        f"/api/projects/p_occ/issues/{issue_id}",
        headers={"X-User-ID": "admin_alice", "If-Match": "2"},
        json={"title": "Updated OCC 2"},
    )
    assert u2.status_code == 200
    assert u2.get_json()["version"] == 3


def test_api_transition_issue_status(client):
    client.post(
        "/api/projects",
        headers={"X-User-ID": "admin_alice"},
        json={"project_id": "p_trans", "name": "Transition Test"},
    )
    iss = client.post(
        "/api/projects/p_trans/issues",
        headers={"X-User-ID": "admin_alice"},
        json={"title": "Transition Issue", "description": "Desc"},
    ).get_json()
    issue_id = iss["issue_id"]

    # OPEN -> IN_PROGRESS with version 1
    t1 = client.post(
        f"/api/projects/p_trans/issues/{issue_id}/transition",
        headers={"X-User-ID": "admin_alice"},
        json={"expected_version": 1, "new_status": "IN_PROGRESS"},
    )
    assert t1.status_code == 200
    assert t1.get_json()["status"] == "IN_PROGRESS"
    assert t1.get_json()["version"] == 2

    # Illegal transition: IN_PROGRESS directly to invalid status string or backwards
    t_illegal = client.post(
        f"/api/projects/p_trans/issues/{issue_id}/transition",
        headers={"X-User-ID": "admin_alice"},
        json={"expected_version": 2, "new_status": "NONEXISTENT_STATUS"},
    )
    assert t_illegal.status_code == 400


def test_api_list_issues_paginated(client):
    client.post(
        "/api/projects",
        headers={"X-User-ID": "admin_alice"},
        json={"project_id": "p_page", "name": "Pagination Test"},
    )
    for i in range(5):
        client.post(
            "/api/projects/p_page/issues",
            headers={"X-User-ID": "admin_alice"},
            json={"title": f"Task {i}", "description": "desc"},
        )

    res = client.get("/api/projects/p_page/issues?limit=3", headers={"X-User-ID": "admin_alice"})
    assert res.status_code == 200
    data = res.get_json()
    assert len(data["items"]) == 3
    assert data["has_more"] is True
    assert data["next_cursor"] is not None
    assert data["total_count"] == 5
