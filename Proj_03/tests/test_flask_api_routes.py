import json


def test_api_create_link_success(client):
    response = client.post(
        "/api/links",
        json={"original_url": "https://stripe.com", "custom_code": "stripe_pay"},
        headers={"X-User-ID": "merchant_1"},
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["short_code"] == "stripe_pay"
    assert data["original_url"] == "https://stripe.com"
    assert data["user_id"] == "merchant_1"
    assert data["hit_count"] == 0


def test_api_create_link_invalid_url(client):
    response = client.post(
        "/api/links",
        json={"original_url": "not_a_valid_url"},
    )
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_api_create_link_duplicate_conflict(client):
    client.post(
        "/api/links",
        json={"original_url": "https://apple.com", "custom_code": "apple_co"},
    )
    dup = client.post(
        "/api/links",
        json={"original_url": "https://orange.com", "custom_code": "apple_co"},
    )
    assert dup.status_code == 409
    assert "already in use" in dup.get_json()["error"]


def test_api_redirect_and_hit_counting(client):
    create_res = client.post(
        "/api/links",
        json={"original_url": "https://github.com"},
    )
    short_code = create_res.get_json()["short_code"]

    # Redirect
    redir_res = client.get(f"/{short_code}")
    assert redir_res.status_code == 302
    assert redir_res.headers["Location"] == "https://github.com"

    # Verify hit count incremented via metadata API
    meta_res = client.get(f"/api/links/{short_code}")
    assert meta_res.status_code == 200
    assert meta_res.get_json()["hit_count"] == 1


def test_api_delete_with_ownership_check(client):
    create_res = client.post(
        "/api/links",
        json={"original_url": "https://secret.org"},
        headers={"X-User-ID": "authorized_user"},
    )
    short_code = create_res.get_json()["short_code"]

    # Unauthorized delete attempt
    del_unauth = client.delete(
        f"/api/links/{short_code}",
        headers={"X-User-ID": "random_hacker"},
    )
    assert del_unauth.status_code == 403

    # Authorized delete
    del_auth = client.delete(
        f"/api/links/{short_code}",
        headers={"X-User-ID": "authorized_user"},
    )
    assert del_auth.status_code == 204

    # Subsequent fetch should be 404
    get_res = client.get(f"/{short_code}")
    assert get_res.status_code == 404


def test_api_get_aggregate_stats(client):
    client.post(
        "/api/links",
        json={"original_url": "https://test1.com"},
    )
    client.post(
        "/api/links",
        json={"original_url": "https://test2.com"},
    )

    stats_res = client.get("/api/stats")
    assert stats_res.status_code == 200
    data = stats_res.get_json()
    assert data["total_links"] >= 2
    assert data["active_links"] >= 2
