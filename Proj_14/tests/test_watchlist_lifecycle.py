import pytest
from Proj_14.src.exceptions import ValidationError, WatchlistNotFoundError


def test_create_and_get_empty_watchlist(service):
    wl = service.create_watchlist(
        user_id="user_alice",
        name="Sci-Fi Favorites",
        description="Top sci-fi movies of all time",
    )

    assert wl.id == 1
    assert wl.user_id == "user_alice"
    assert wl.name == "Sci-Fi Favorites"
    assert wl.description == "Top sci-fi movies of all time"
    assert wl.movie_count == 0
    assert wl.movies == []
    assert wl.created_at is not None
    assert wl.updated_at == wl.created_at

    fetched = service.get_watchlist(wl.id, "user_alice")
    assert fetched.id == wl.id
    assert fetched.name == "Sci-Fi Favorites"
    assert fetched.movie_count == 0


def test_list_watchlists_for_user(service):
    service.create_watchlist("user_alice", "List 1")
    service.create_watchlist("user_alice", "List 2")
    service.create_watchlist("user_bob", "Bob's List")

    alice_lists = service.list_watchlists("user_alice")
    assert len(alice_lists) == 2
    assert [w.name for w in alice_lists] == ["List 1", "List 2"]

    bob_lists = service.list_watchlists("user_bob")
    assert len(bob_lists) == 1
    assert bob_lists[0].name == "Bob's List"


def test_rename_watchlist(service):
    wl = service.create_watchlist("user_alice", "Old Name")
    renamed = service.rename_watchlist(wl.id, "user_alice", "New Refined Name")

    assert renamed.id == wl.id
    assert renamed.name == "New Refined Name"
    assert renamed.updated_at >= renamed.created_at

    fetched = service.get_watchlist(wl.id, "user_alice")
    assert fetched.name == "New Refined Name"


def test_delete_watchlist_cascades_movies(service):
    wl = service.create_watchlist("user_alice", "To Delete")
    service.add_movie(wl.id, "user_alice", "m_matrix", "The Matrix")

    assert len(service.get_watchlist_movies(wl.id, "user_alice")) == 1

    success = service.delete_watchlist(wl.id, "user_alice")
    assert success is True

    # Verification: Watchlist should no longer exist
    with pytest.raises(WatchlistNotFoundError):
        service.get_watchlist(wl.id, "user_alice")

    assert len(service.list_watchlists("user_alice")) == 0


def test_input_validation_errors(service):
    with pytest.raises(ValidationError):
        service.create_watchlist("", "Valid Name")

    with pytest.raises(ValidationError):
        service.create_watchlist("user_alice", "")

    with pytest.raises(ValidationError):
        service.create_watchlist("user_alice", "   \t\n")

    with pytest.raises(ValidationError):
        service.rename_watchlist(1, "user_alice", "")

    with pytest.raises(ValidationError):
        service.rename_watchlist(0, "user_alice", "New Name")
