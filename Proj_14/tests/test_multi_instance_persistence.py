import pytest
from Proj_14.src.service import ScreenShelf


def test_separate_service_instances_observe_committed_state(file_db_service):
    """CRITICAL BUG FIX VERIFICATION:

    All writes must be committed immediately so that independent service instances
    sharing the same database observe all creations, mutations, and deletions.
    """
    shelf_a, db_path = file_db_service

    # Instance A creates a watchlist and adds a movie
    wl = shelf_a.create_watchlist("user_alice", "Shared DB List", description="Initial description")
    shelf_a.add_movie(wl.id, "user_alice", "m_godfather", "The Godfather")

    # Instance B connects to the exact same database file
    shelf_b = ScreenShelf(db_path=db_path)

    # Instance B MUST immediately see the watchlist and movie committed by Instance A
    wl_from_b = shelf_b.get_watchlist(wl.id, "user_alice")
    assert wl_from_b.name == "Shared DB List"
    assert wl_from_b.movie_count == 1
    assert wl_from_b.movies[0].movie_id == "m_godfather"

    # Instance B adds a second movie and renames the watchlist
    shelf_b.add_movie(wl.id, "user_alice", "m_pulp", "Pulp Fiction")
    shelf_b.rename_watchlist(wl.id, "user_alice", "Updated By Instance B")

    # Instance A MUST immediately observe the changes committed by Instance B
    wl_from_a = shelf_a.get_watchlist(wl.id, "user_alice")
    assert wl_from_a.name == "Updated By Instance B"
    assert wl_from_a.movie_count == 2
    assert [m.movie_id for m in wl_from_a.movies] == ["m_godfather", "m_pulp"]

    # Instance A closes connection; Instance B must continue to operate without data loss
    shelf_a.close()

    movies_b = shelf_b.get_watchlist_movies(wl.id, "user_alice")
    assert len(movies_b) == 2

    # Clean up
    shelf_b.close()


def test_persistence_across_service_restarts(tmp_path):
    """Verify data survives full shutdown and reconnect cycles."""
    db_file = str(tmp_path / "persistence_restart.db")

    # Cycle 1: Write data
    shelf_1 = ScreenShelf(db_path=db_file)
    wl1 = shelf_1.create_watchlist("user_alice", "Persistent List")
    shelf_1.add_movie(wl1.id, "user_alice", "m_inception", "Inception")
    shelf_1.close()

    # Cycle 2: Read data after restart
    shelf_2 = ScreenShelf(db_path=db_file)
    restored = shelf_2.get_watchlist(wl1.id, "user_alice")
    assert restored.name == "Persistent List"
    assert restored.movie_count == 1
    assert restored.movies[0].title == "Inception"
    shelf_2.close()
