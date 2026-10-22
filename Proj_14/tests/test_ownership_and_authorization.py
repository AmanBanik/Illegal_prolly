import pytest
from Proj_14.src.exceptions import UnauthorizedError, WatchlistNotFoundError


def test_private_watchlist_ownership_checks(service):
    wl_alice = service.create_watchlist("user_alice", "Alice Secret List")

    # Bob attempts to get Alice's watchlist
    with pytest.raises(UnauthorizedError) as exc_info:
        service.get_watchlist(wl_alice.id, "user_bob")
    assert "not authorized" in str(exc_info.value)
    assert exc_info.value.status_code == 403

    # Bob attempts to add a movie to Alice's watchlist
    with pytest.raises(UnauthorizedError):
        service.add_movie(wl_alice.id, "user_bob", "m_alien", "Alien")

    # Bob attempts to rename Alice's watchlist
    with pytest.raises(UnauthorizedError):
        service.rename_watchlist(wl_alice.id, "user_bob", "Hacked Name")

    # Bob attempts to remove a movie from Alice's watchlist
    service.add_movie(wl_alice.id, "user_alice", "m_alien", "Alien")
    with pytest.raises(UnauthorizedError):
        service.remove_movie(wl_alice.id, "user_bob", "m_alien")

    # Bob attempts to delete Alice's watchlist
    with pytest.raises(UnauthorizedError):
        service.delete_watchlist(wl_alice.id, "user_bob")

    # Bob listing watchlists should see 0
    assert len(service.list_watchlists("user_bob")) == 0

    # Alice still has her watchlist untouched
    fetched = service.get_watchlist(wl_alice.id, "user_alice")
    assert fetched.name == "Alice Secret List"
    assert fetched.movie_count == 1


def test_access_nonexistent_watchlist_raises_not_found(service):
    with pytest.raises(WatchlistNotFoundError):
        service.get_watchlist(999, "user_alice")

    with pytest.raises(WatchlistNotFoundError):
        service.add_movie(999, "user_alice", "m_1", "Movie")

    with pytest.raises(WatchlistNotFoundError):
        service.delete_watchlist(999, "user_alice")
