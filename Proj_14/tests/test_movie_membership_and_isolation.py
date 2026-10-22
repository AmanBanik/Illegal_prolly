import pytest
from Proj_14.src.exceptions import MovieNotFoundError


def test_cross_watchlist_movie_isolation_on_removal(service):
    """CRITICAL BUG FIX VERIFICATION:

    Removing a movie from Watchlist A must NEVER remove that movie from Watchlist B.
    """
    wl_a = service.create_watchlist("user_alice", "Alice Watchlist A")
    wl_b = service.create_watchlist("user_alice", "Alice Watchlist B")

    # Add the same movie to both watchlists
    movie_id = "m_interstellar"
    movie_title = "Interstellar"
    service.add_movie(wl_a.id, "user_alice", movie_id, movie_title, metadata={"year": 2014})
    service.add_movie(wl_b.id, "user_alice", movie_id, movie_title, metadata={"year": 2014})

    # Verify both watchlists contain the movie
    movies_a = service.get_watchlist_movies(wl_a.id, "user_alice")
    movies_b = service.get_watchlist_movies(wl_b.id, "user_alice")
    assert len(movies_a) == 1
    assert len(movies_b) == 1
    assert movies_a[0].movie_id == movie_id
    assert movies_b[0].movie_id == movie_id

    # Remove movie from Watchlist A ONLY
    removed = service.remove_movie(wl_a.id, "user_alice", movie_id)
    assert removed is True

    # VERIFICATION: Watchlist A must now be empty
    movies_a_after = service.get_watchlist_movies(wl_a.id, "user_alice")
    assert len(movies_a_after) == 0

    # VERIFICATION: Watchlist B MUST STILL CONTAIN the movie!
    movies_b_after = service.get_watchlist_movies(wl_b.id, "user_alice")
    assert len(movies_b_after) == 1
    assert movies_b_after[0].movie_id == movie_id
    assert movies_b_after[0].title == "Interstellar"
    assert movies_b_after[0].metadata == {"year": 2014}


def test_movie_metadata_and_ordering(service):
    wl = service.create_watchlist("user_alice", "Cinema Classics")

    service.add_movie(wl.id, "user_alice", "m_1", "Movie One", metadata={"rating": 8.5})
    service.add_movie(wl.id, "user_alice", "m_2", "Movie Two", metadata={"rating": 9.0})
    service.add_movie(wl.id, "user_alice", "m_3", "Movie Three", metadata={"rating": 7.8})

    movies = service.get_watchlist_movies(wl.id, "user_alice")
    assert len(movies) == 3
    assert [m.movie_id for m in movies] == ["m_1", "m_2", "m_3"]
    assert movies[0].metadata == {"rating": 8.5}
    assert movies[1].metadata == {"rating": 9.0}


def test_remove_nonexistent_movie_raises_error(service):
    wl = service.create_watchlist("user_alice", "My List")

    with pytest.raises(MovieNotFoundError) as exc_info:
        service.remove_movie(wl.id, "user_alice", "m_ghost")
    assert "not found in watchlist" in str(exc_info.value)
