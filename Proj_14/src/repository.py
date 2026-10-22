from datetime import datetime, timezone
import json
import sqlite3
import threading
from typing import Any, Dict, List, Optional
from .exceptions import DuplicateMovieError
from .models import MovieItem, Watchlist


class WatchlistRepository:
    """Thread-safe SQLite repository with immediate commit guarantees."""

    def __init__(self, db_path: str = ":memory:"):
        self._db_path = db_path
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(
            self._db_path,
            timeout=30.0,
            check_same_thread=False,
        )
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("PRAGMA journal_mode = WAL;")
            cursor.execute("PRAGMA foreign_keys = ON;")
            cursor.execute("PRAGMA synchronous = NORMAL;")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS watchlists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_watchlists_user ON watchlists(user_id);")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS watchlist_movies (
                    watchlist_id INTEGER NOT NULL,
                    movie_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    added_at TEXT NOT NULL,
                    metadata TEXT,
                    PRIMARY KEY (watchlist_id, movie_id),
                    FOREIGN KEY (watchlist_id) REFERENCES watchlists(id) ON DELETE CASCADE
                );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_watchlist_movies_wid ON watchlist_movies(watchlist_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_watchlist_movies_mid ON watchlist_movies(movie_id);")
            self._conn.commit()

    def create_watchlist(
        self,
        user_id: str,
        name: str,
        description: Optional[str],
        now: datetime,
    ) -> int:
        """Inserts a new watchlist and commits immediately."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                """
                INSERT INTO watchlists (user_id, name, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    name,
                    description,
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
            watchlist_id = cursor.lastrowid
            self._conn.commit()
            return watchlist_id

    def get_watchlist_record(self, watchlist_id: int) -> Optional[Dict[str, Any]]:
        """Fetches raw watchlist row without movies."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                "SELECT * FROM watchlists WHERE id = ?",
                (watchlist_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return dict(row)

    def list_watchlist_records_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Fetches all watchlist rows for a user ordered by created_at ASC."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                "SELECT * FROM watchlists WHERE user_id = ? ORDER BY id ASC",
                (user_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def rename_watchlist(self, watchlist_id: int, new_name: str, now: datetime) -> bool:
        """Updates watchlist name and timestamp, committing immediately."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                """
                UPDATE watchlists
                SET name = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_name, now.isoformat(), watchlist_id),
            )
            updated = cursor.rowcount > 0
            self._conn.commit()
            return updated

    def delete_watchlist(self, watchlist_id: int) -> bool:
        """Deletes a watchlist and all associated movies, committing immediately."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("DELETE FROM watchlist_movies WHERE watchlist_id = ?", (watchlist_id,))
            cursor.execute("DELETE FROM watchlists WHERE id = ?", (watchlist_id,))
            deleted = cursor.rowcount > 0
            self._conn.commit()
            return deleted

    def add_movie(
        self,
        watchlist_id: int,
        movie_id: str,
        title: str,
        added_at: datetime,
        metadata: Optional[Dict[str, Any]],
    ) -> None:
        """Inserts a movie into the target watchlist, committing immediately.

        Raises:
            DuplicateMovieError: if the movie already exists in this watchlist.
        """
        metadata_str = json.dumps(metadata) if metadata else None
        with self._lock:
            cursor = self._conn.cursor()
            try:
                cursor.execute(
                    """
                    INSERT INTO watchlist_movies (watchlist_id, movie_id, title, added_at, metadata)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        watchlist_id,
                        movie_id,
                        title,
                        added_at.isoformat(),
                        metadata_str,
                    ),
                )
                self._conn.commit()
            except sqlite3.IntegrityError as e:
                self._conn.rollback()
                raise DuplicateMovieError(
                    f"Movie '{movie_id}' already exists in watchlist #{watchlist_id}"
                ) from e

    def remove_movie(self, watchlist_id: int, movie_id: str) -> bool:
        """Removes a movie strictly from the specified watchlist, committing immediately."""
        with self._lock:
            cursor = self._conn.cursor()
            # Strict scoping to target watchlist_id prevents cross-watchlist accidental deletion
            cursor.execute(
                """
                DELETE FROM watchlist_movies
                WHERE watchlist_id = ? AND movie_id = ?
                """,
                (watchlist_id, movie_id),
            )
            removed = cursor.rowcount > 0
            self._conn.commit()
            return removed

    def get_movies_for_watchlist(self, watchlist_id: int) -> List[MovieItem]:
        """Fetches all movies for a given watchlist ordered by added_at ASC."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                """
                SELECT movie_id, title, added_at, metadata
                FROM watchlist_movies
                WHERE watchlist_id = ?
                ORDER BY added_at ASC, rowid ASC
                """,
                (watchlist_id,),
            )
            items = []
            for row in cursor.fetchall():
                added_at = datetime.fromisoformat(row["added_at"])
                if added_at.tzinfo is None:
                    added_at = added_at.replace(tzinfo=timezone.utc)

                meta = None
                if row["metadata"]:
                    try:
                        meta = json.loads(row["metadata"])
                    except Exception:
                        meta = None

                items.append(
                    MovieItem(
                        movie_id=row["movie_id"],
                        title=row["title"],
                        added_at=added_at,
                        metadata=meta,
                    )
                )
            return items

    def movie_exists_in_watchlist(self, watchlist_id: int, movie_id: str) -> bool:
        """Checks if a movie is present in a specific watchlist."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                "SELECT 1 FROM watchlist_movies WHERE watchlist_id = ? AND movie_id = ? LIMIT 1",
                (watchlist_id, movie_id),
            )
            return cursor.fetchone() is not None

    def close(self) -> None:
        """Closes the underlying SQLite connection."""
        with self._lock:
            try:
                self._conn.commit()
            except Exception:
                pass
            self._conn.close()
