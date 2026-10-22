"""Integration tests for the Flask REST API endpoints."""

from flask.testing import FlaskClient


def test_api_add_comment_success(client: FlaskClient) -> None:
    """Verify POST /api/posts/<post_id>/comments creates comment and returns 201."""
    resp = client.post(
        "/api/posts/post_123/comments",
        json={"author_id": "alice", "content": "REST comment test"},
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["status"] == "success"
    assert data["data"]["id"] == 1
    assert data["data"]["post_id"] == "post_123"
    assert data["data"]["author_id"] == "alice"
    assert data["data"]["content"] == "REST comment test"
    assert data["data"]["replies"] == []


def test_api_add_comment_invalid_payload(client: FlaskClient) -> None:
    """Verify validation failure returns 400 Bad Request."""
    # Missing fields
    resp = client.post("/api/posts/p1/comments", json={"author_id": "alice"})
    assert resp.status_code == 400
    assert resp.get_json()["type"] == "ValidationError"

    # Whitespace content
    resp = client.post("/api/posts/p1/comments", json={"author_id": "alice", "content": "   "})
    assert resp.status_code == 400


def test_api_get_comments_for_post(client: FlaskClient) -> None:
    """Verify GET /api/posts/<post_id>/comments returns full thread."""
    client.post("/api/posts/post_thread/comments", json={"author_id": "u1", "content": "First"})
    client.post("/api/posts/post_thread/comments", json={"author_id": "u2", "content": "Second"})

    resp = client.get("/api/posts/post_thread/comments")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert data["count"] == 2
    assert len(data["data"]) == 2
    assert data["data"][0]["content"] == "First"
    assert data["data"][1]["content"] == "Second"


def test_api_add_reply_success(client: FlaskClient) -> None:
    """Verify POST /api/comments/<comment_id>/replies creates reply and returns 201."""
    comment_resp = client.post(
        "/api/posts/post_rep/comments", json={"author_id": "alice", "content": "Parent"}
    )
    comment_id = comment_resp.get_json()["data"]["id"]

    resp = client.post(
        f"/api/comments/{comment_id}/replies",
        json={"author_id": "bob", "content": "Child reply"},
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["status"] == "success"
    assert data["data"]["id"] == 1
    assert data["data"]["comment_id"] == comment_id
    assert data["data"]["content"] == "Child reply"


def test_api_add_reply_hierarchy_violation(client: FlaskClient) -> None:
    """Verify attempting to reply to a reply returns 400 InvalidHierarchyError."""
    # Add comment
    c_resp = client.post(
        "/api/posts/post_hier/comments", json={"author_id": "alice", "content": "Parent"}
    )
    c_id = c_resp.get_json()["data"]["id"]

    # Add reply
    r_resp = client.post(
        f"/api/comments/{c_id}/replies", json={"author_id": "bob", "content": "Level 2 reply"}
    )
    r_id = r_resp.get_json()["data"]["id"]

    # Attempt reply to reply via /api/replies/<id>/replies route
    nested_resp = client.post(
        f"/api/replies/{r_id}/replies",
        json={"author_id": "charlie", "content": "Level 3 illegal attempt"},
    )
    assert nested_resp.status_code == 400
    data = nested_resp.get_json()
    assert data["type"] == "InvalidHierarchyError"

    # Attempt reply to reply via target_type payload
    target_resp = client.post(
        f"/api/comments/{r_id}/replies",
        json={"author_id": "charlie", "content": "Level 3 attempt", "target_type": "reply"},
    )
    assert target_resp.status_code == 400
    assert target_resp.get_json()["type"] == "InvalidHierarchyError"


def test_api_not_found_handling(client: FlaskClient) -> None:
    """Verify non-existent IDs return 404."""
    resp = client.get("/api/comments/9999")
    assert resp.status_code == 404
    assert resp.get_json()["type"] == "CommentNotFoundError"

    resp2 = client.post(
        "/api/comments/9999/replies", json={"author_id": "alice", "content": "text"}
    )
    assert resp2.status_code == 404


def test_api_get_comment_and_replies(client: FlaskClient) -> None:
    """Verify individual comment and replies retrieval."""
    c_resp = client.post(
        "/api/posts/p_nested/comments", json={"author_id": "u1", "content": "Discussion"}
    )
    c_id = c_resp.get_json()["data"]["id"]

    client.post(f"/api/comments/{c_id}/replies", json={"author_id": "u2", "content": "Reply 1"})
    client.post(f"/api/comments/{c_id}/replies", json={"author_id": "u3", "content": "Reply 2"})

    # Get single comment
    resp = client.get(f"/api/comments/{c_id}")
    assert resp.status_code == 200
    assert len(resp.get_json()["data"]["replies"]) == 2

    # Get replies directly
    replies_resp = client.get(f"/api/comments/{c_id}/replies")
    assert replies_resp.status_code == 200
    assert replies_resp.get_json()["count"] == 2


def test_api_get_stats(client: FlaskClient) -> None:
    """Verify GET /api/stats endpoint."""
    client.post("/api/posts/p_stat/comments", json={"author_id": "u1", "content": "C1"})
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["total_posts"] == 1
    assert data["total_comments"] == 1
    assert data["total_replies"] == 0
