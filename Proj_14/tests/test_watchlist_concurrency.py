import concurrent.futures
import pytest
from Proj_14.src.exceptions import DuplicateMovieError


def test_concurrent_movie_additions_distinct_movies(service):
    """Verify that multiple concurrent threads adding distinct movies to a watchlist

    all succeed without deadlocks or lost writes.
    """
    wl = service.create_watchlist("user_alice", "High Throughput Watchlist")
    num_threads = 20

    def add_task(i: int):
        return service.add_movie(
            watchlist_id=wl.id,
            user_id="user_alice",
            movie_id=f"movie_{i}",
            title=f"Movie Title {i}",
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(add_task, i) for i in range(num_threads)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(results) == num_threads

    movies = service.get_watchlist_movies(wl.id, "user_alice")
    assert len(movies) == num_threads
    movie_ids = {m.movie_id for m in movies}
    assert movie_ids == {f"movie_{i}" for i in range(num_threads)}


def test_concurrent_duplicate_movie_race_single_winner(service):
    """Verify that when multiple threads attempt to insert the exact same movie

    into a watchlist concurrently, exactly 1 succeeds and all others raise DuplicateMovieError.
    """
    wl = service.create_watchlist("user_alice", "Race Watchlist")
    num_threads = 15
    target_movie_id = "movie_rare_gem"

    success_count = 0
    duplicate_count = 0

    def race_task(i: int):
        return service.add_movie(
            watchlist_id=wl.id,
            user_id="user_alice",
            movie_id=target_movie_id,
            title="Rare Gem",
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(race_task, i) for i in range(num_threads)]
        for f in concurrent.futures.as_completed(futures):
            try:
                f.result()
                success_count += 1
            except DuplicateMovieError:
                duplicate_count += 1

    assert success_count == 1, f"Expected 1 winner, got {success_count}"
    assert duplicate_count == num_threads - 1, f"Expected {num_threads - 1} duplicates, got {duplicate_count}"

    movies = service.get_watchlist_movies(wl.id, "user_alice")
    assert len(movies) == 1
    assert movies[0].movie_id == target_movie_id
