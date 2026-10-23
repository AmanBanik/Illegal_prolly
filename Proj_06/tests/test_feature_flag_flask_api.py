"""Integration tests for the Flask REST API endpoints."""

from flask.testing import FlaskClient


def test_api_create_flag_success(client: FlaskClient) -> None:
    """Verify POST /api/flags creates a feature flag and returns 201."""
    payload = {
        "key": "recommendation_engine_v2",
        "name": "Rec Engine V2",
        "description": "Collaborative filtering rollout",
        "enabled": True,
        "variants": [{"key": "legacy"}, {"key": "collab_v2", "attachment": {"model": "bert"}}],
        "default_variant": "legacy",
        "rules": [
            {
                "id": "beta_users",
                "variant_key": "collab_v2",
                "conditions": [{"attribute": "beta", "operator": "EQUALS", "value": True}],
            }
        ],
        "rollout": {
            "variants": [
                {"variant_key": "collab_v2", "weight": 20.0},
                {"variant_key": "legacy", "weight": 80.0},
            ]
        },
    }

    resp = client.post("/api/flags", json=payload)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["status"] == "success"
    assert data["data"]["key"] == "recommendation_engine_v2"
    assert len(data["data"]["rules"]) == 1
    assert data["data"]["rollout"]["variants"][0]["weight"] == 20.0


def test_api_create_flag_conflict_and_validation(client: FlaskClient) -> None:
    """Verify 409 Conflict on duplicate key and 400 Bad Request on invalid payloads."""
    payload = {
        "key": "dup_key",
        "name": "Original",
        "variants": ["off", "on"],
        "default_variant": "off",
    }
    resp1 = client.post("/api/flags", json=payload)
    assert resp1.status_code == 201

    # Conflict
    resp2 = client.post("/api/flags", json=payload)
    assert resp2.status_code == 409
    assert resp2.get_json()["type"] == "FlagAlreadyExistsError"

    # Validation Error (missing default_variant)
    bad_payload = {"key": "bad_flag", "name": "Bad", "variants": ["v1"]}
    resp3 = client.post("/api/flags", json=bad_payload)
    assert resp3.status_code == 400
    assert resp3.get_json()["type"] == "ValidationError"


def test_api_get_and_list_flags(client: FlaskClient) -> None:
    """Verify GET /api/flags and GET /api/flags/<key>."""
    client.post("/api/flags", json={"key": "f_list_1", "name": "F1", "variants": ["a"], "default_variant": "a"})
    client.post("/api/flags", json={"key": "f_list_2", "name": "F2", "variants": ["b"], "default_variant": "b"})

    # List flags
    resp_list = client.get("/api/flags")
    assert resp_list.status_code == 200
    assert resp_list.get_json()["count"] >= 2

    # Get single flag
    resp_single = client.get("/api/flags/f_list_1")
    assert resp_single.status_code == 200
    assert resp_single.get_json()["data"]["name"] == "F1"

    # Not found
    resp_404 = client.get("/api/flags/non_existent_key")
    assert resp_404.status_code == 404
    assert resp_404.get_json()["type"] == "FlagNotFoundError"


def test_api_update_and_delete_flag(client: FlaskClient) -> None:
    """Verify PUT and DELETE endpoints."""
    client.post("/api/flags", json={"key": "up_flag", "name": "Before", "variants": ["off", "on"], "default_variant": "off"})

    # Update
    update_resp = client.put("/api/flags/up_flag", json={"name": "After", "enabled": False})
    assert update_resp.status_code == 200
    assert update_resp.get_json()["data"]["name"] == "After"
    assert update_resp.get_json()["data"]["enabled"] is False

    # Delete
    del_resp = client.delete("/api/flags/up_flag")
    assert del_resp.status_code == 200

    # Ensure deleted
    get_del = client.get("/api/flags/up_flag")
    assert get_del.status_code == 404


def test_api_evaluate_flag_and_evaluate_all(client: FlaskClient) -> None:
    """Verify evaluation endpoints with context attributes."""
    flag_payload = {
        "key": "search_algorithm",
        "name": "Search Algo",
        "enabled": True,
        "variants": [{"key": "classic"}, {"key": "neural_v2", "attachment": {"dim": 512}}],
        "default_variant": "classic",
        "rules": [
            {
                "id": "vip_rule",
                "variant_key": "neural_v2",
                "conditions": [{"attribute": "vip", "operator": "EQUALS", "value": True}],
            }
        ],
    }
    client.post("/api/flags", json=flag_payload)

    # Evaluate VIP user -> neural_v2 (RULE_MATCH)
    eval_vip = client.post(
        "/api/flags/search_algorithm/evaluate",
        json={"user_id": "vip_user_42", "attributes": {"vip": True}},
    )
    assert eval_vip.status_code == 200
    data_vip = eval_vip.get_json()["data"]
    assert data_vip["variant_key"] == "neural_v2"
    assert data_vip["reason"] == "RULE_MATCH"
    assert data_vip["attachment"]["dim"] == 512

    # Evaluate standard user -> classic (DEFAULT_FALLBACK)
    eval_std = client.post(
        "/api/flags/search_algorithm/evaluate",
        json={"user_id": "std_user_99", "attributes": {"vip": False}},
    )
    assert eval_std.status_code == 200
    assert eval_std.get_json()["data"]["variant_key"] == "classic"
    assert eval_std.get_json()["data"]["reason"] == "DEFAULT_FALLBACK"

    # Evaluate all
    eval_all = client.post(
        "/api/evaluate",
        json={"user_id": "vip_user_42", "attributes": {"vip": True}},
    )
    assert eval_all.status_code == 200
    assert "search_algorithm" in eval_all.get_json()["data"]


def test_api_stats(client: FlaskClient) -> None:
    """Verify GET /api/stats endpoint."""
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    stats = resp.get_json()["data"]
    assert "total_flags" in stats
    assert "active_flags" in stats
