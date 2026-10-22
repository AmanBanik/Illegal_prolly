import pytest
from Proj_14.src.exceptions import DuplicateMovieError


def test_adding_duplicate_movie_to_same_watchlist_raises_duplicate_error(service):
    """CRITICAL BUG FIX VERIFICATION:

    Adding the same movie to the same watchlist must raise DuplicateMovieError (HTTP 409).
    """
    wl = service.create_watchlist("user_alice", "Favorites")
    movie_id = "m_oppenheimer"

    # First addition succeeds
    item1 = service.add_movie(wl.id, "user_alice", movie_id, "Oppenheimer")
    assert item1.movie_id == movie_id

    # Second addition raises DuplicateMovieError
    with pytest.raises(DuplicateMovieError) as exc_info:
        service.add_movie(wl.id, "user_alice", movie_id, "Oppenheimer Duplicate")
    assert f"Movie '{movie_id}' already exists in watchlist #{wl.id}" in str(exc_info.value)
    assert exc_info.value.status_code == 409

    # Verify count remains exactly 1
    movies = service.get_watchlist_movies(wl.id, "user_alice")
    assert len(movies) == 1
    assert movies[0].title == "Oppenheimer"


def test_same_movie_can_exist_in_different_watchlists(service):
    """The uniqueness constraint is scoped per (watchlist_id, movie_id)."""
    wl1 = service.create_watchlist("user_alice", "List A")
    wl2 = service.create_watchlist("user_alice", "List B")

    service.add_movie(wl1.id, "user_alice", "m_dune", "Dune")
    service.add_movie(wl2.id, "user_alice", "m_dune", "Dune")

    assert len(service.get_watchlist_movies(wl1.id, "user_alice")) == 1
    assert len(service.get_watchlist_movies(wl2.id, "user_alice")) == 1
