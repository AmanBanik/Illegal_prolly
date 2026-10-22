import json
import pytest


def test_api_create_watchlist(client):
    resp = client.post(
        "/api/watchlists",
        headers={"X-User-ID": "user_alice"},
        json={"name": "Alice Watchlist", "description": "Awesome movies"},
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["name"] == "Alice Watchlist"
    assert data["description"] == "Awesome movies"
    assert data["id"] == 1
    assert data["movie_count"] == 0


def test_api_list_watchlists(client):
    client.post(
        "/api/watchlists",
        headers={"X-User-ID": "user_alice"},
        json={"name": "Alice List 1"},
    )
    client.post(
        "/api/watchlists",
        headers={"X-User-ID": "user_alice"},
        json={"name": "Alice List 2"},
    )

    resp = client.get("/api/watchlists", headers={"X-User-ID": "user_alice"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 2
    assert [w["name"] for w in data] == ["Alice List 1", "Alice List 2"]


def test_api_missing_auth_header(client):
    resp = client.post("/api/watchlists", json={"name": "No Auth"})
    assert resp.status_code == 401
    assert "Missing or empty 'X-User-ID'" in resp.get_json()["error"]


def test_api_get_watchlist_and_ownership(client):
    create_resp = client.post(
        "/api/watchlists",
        headers={"X-User-ID": "user_alice"},
        json={"name": "Alice Secret"},
    )
    wl_id = create_resp.get_json()["id"]

    # Alice accesses -> 200 OK
    resp = client.get(f"/api/watchlists/{wl_id}", headers={"X-User-ID": "user_alice"})
    assert resp.status_code == 200

    # Bob accesses -> 403 Forbidden
    resp_bob = client.get(f"/api/watchlists/{wl_id}", headers={"X-User-ID": "user_bob"})
    assert resp_bob.status_code == 403

    # Non-existent ID -> 404 Not Found
    resp_404 = client.get("/api/watchlists/999", headers={"X-User-ID": "user_alice"})
    assert resp_404.status_code == 404


def test_api_rename_watchlist(client):
    create_resp = client.post(
        "/api/watchlists",
        headers={"X-User-ID": "user_alice"},
        json={"name": "Old Title"},
    )
    wl_id = create_resp.get_json()["id"]

    resp = client.patch(
        f"/api/watchlists/{wl_id}",
        headers={"X-User-ID": "user_alice"},
        json={"name": "New Title"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["name"] == "New Title"


def test_api_add_and_remove_movie_and_duplicate_conflict(client):
    create_resp = client.post(
        "/api/watchlists",
        headers={"X-User-ID": "user_alice"},
        json={"name": "Cinema"},
    )
    wl_id = create_resp.get_json()["id"]

    # Add movie -> 201 Created
    add_resp = client.post(
        f"/api/watchlists/{wl_id}/movies",
        headers={"X-User-ID": "user_alice"},
        json={"movie_id": "m_parasite", "title": "Parasite", "metadata": {"director": "Bong Joon-ho"}},
    )
    assert add_resp.status_code == 201
    assert add_resp.get_json()["movie_id"] == "m_parasite"

    # Add same movie again -> 409 Conflict
    dup_resp = client.post(
        f"/api/watchlists/{wl_id}/movies",
        headers={"X-User-ID": "user_alice"},
        json={"movie_id": "m_parasite", "title": "Parasite"},
    )
    assert dup_resp.status_code == 409
    assert "already exists in watchlist" in dup_resp.get_json()["error"]

    # Remove movie -> 200 OK
    del_resp = client.delete(
        f"/api/watchlists/{wl_id}/movies/m_parasite",
        headers={"X-User-ID": "user_alice"},
    )
    assert del_resp.status_code == 200

    # Remove non-existent movie -> 404 Not Found
    del_resp_again = client.delete(
        f"/api/watchlists/{wl_id}/movies/m_parasite",
        headers={"X-User-ID": "user_alice"},
    )
    assert del_resp_again.status_code == 404


def test_api_delete_watchlist(client):
    create_resp = client.post(
        "/api/watchlists",
        headers={"X-User-ID": "user_alice"},
        json={"name": "To be deleted"},
    )
    wl_id = create_resp.get_json()["id"]

    del_resp = client.delete(
        f"/api/watchlists/{wl_id}",
        headers={"X-User-ID": "user_alice"},
    )
    assert del_resp.status_code == 200

    get_resp = client.get(
        f"/api/watchlists/{wl_id}",
        headers={"X-User-ID": "user_alice"},
    )
    assert get_resp.status_code == 404
