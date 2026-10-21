import sqlite3
import threading
from datetime import datetime, timezone
from typing import Optional
from .models import AggregateStats, LinkRecord


class LinkRepository:
    """Thread-safe SQLite repository managing URL mapping persistence."""

    def __init__(self, db_path: str = ":memory:"):
        self._db_path = db_path
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(
            self._db_path,
            timeout=30.0,
            check_same_thread=False,
            isolation_level=None,  # Autocommit mode for explicit transaction management
        )
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("PRAGMA journal_mode = WAL;")
            cursor.execute("PRAGMA synchronous = NORMAL;")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    short_code TEXT UNIQUE NOT NULL,
                    original_url TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    hit_count INTEGER DEFAULT 0,
                    is_deleted INTEGER DEFAULT 0
                );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_short_code ON links(short_code);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON links(user_id);")

    def _row_to_record(self, row: sqlite3.Row) -> LinkRecord:
        created_at = datetime.fromisoformat(row["created_at"])
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        expires_at = None
        if row["expires_at"]:
            expires_at = datetime.fromisoformat(row["expires_at"])
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)

        return LinkRecord(
            short_code=row["short_code"],
            original_url=row["original_url"],
            user_id=row["user_id"],
            created_at=created_at,
            expires_at=expires_at,
            hit_count=row["hit_count"],
            is_deleted=bool(row["is_deleted"]),
        )

    def save_link(self, record: LinkRecord) -> None:
        """Inserts a new link record into the database."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                """
                INSERT INTO links (short_code, original_url, user_id, created_at, expires_at, hit_count, is_deleted)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.short_code,
                    record.original_url,
                    record.user_id,
                    record.created_at.isoformat(),
                    record.expires_at.isoformat() if record.expires_at else None,
                    record.hit_count,
                    1 if record.is_deleted else 0,
                ),
            )

    def get_by_code(self, short_code: str) -> Optional[LinkRecord]:
        """Fetches link by short_code."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("SELECT * FROM links WHERE short_code = ?", (short_code,))
            row = cursor.fetchone()
            return self._row_to_record(row) if row else None

    def code_exists(self, short_code: str) -> bool:
        """Checks if a short code is already taken (including deleted ones to prevent reuse)."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("SELECT 1 FROM links WHERE short_code = ? LIMIT 1", (short_code,))
            return cursor.fetchone() is not None

    def increment_hit(self, short_code: str) -> bool:
        """Atomically increments hit count for an active link under concurrency."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                """
                UPDATE links
                SET hit_count = hit_count + 1
                WHERE short_code = ? AND is_deleted = 0
                """,
                (short_code,),
            )
            return cursor.rowcount > 0

    def soft_delete(self, short_code: str) -> bool:
        """Marks a link as deleted."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                "UPDATE links SET is_deleted = 1 WHERE short_code = ? AND is_deleted = 0",
                (short_code,),
            )
            return cursor.rowcount > 0

    def get_aggregate_stats(
        self, user_id: Optional[str] = None, current_time: Optional[datetime] = None
    ) -> AggregateStats:
        """Calculates aggregate metrics across links."""
        now = (current_time or datetime.now(timezone.utc)).isoformat()
        with self._lock:
            cursor = self._conn.cursor()
            base_query = "FROM links"
            params = []
            if user_id:
                base_query += " WHERE user_id = ?"
                params.append(user_id)

            # Total links
            cursor.execute(f"SELECT COUNT(*) {base_query}", params)
            total_links = cursor.fetchone()[0]

            # Total hits
            cursor.execute(f"SELECT COALESCE(SUM(hit_count), 0) {base_query}", params)
            total_hits = cursor.fetchone()[0]

            # Deleted links
            del_clause = "WHERE is_deleted = 1" if not user_id else "WHERE user_id = ? AND is_deleted = 1"
            cursor.execute(f"SELECT COUNT(*) FROM links {del_clause}", params)
            deleted_links = cursor.fetchone()[0]

            # Expired links (not deleted, but expires_at <= now)
            exp_clause = (
                "WHERE is_deleted = 0 AND expires_at IS NOT NULL AND expires_at <= ?"
                if not user_id
                else "WHERE user_id = ? AND is_deleted = 0 AND expires_at IS NOT NULL AND expires_at <= ?"
            )
            exp_params = [now] if not user_id else [user_id, now]
            cursor.execute(f"SELECT COUNT(*) FROM links {exp_clause}", exp_params)
            expired_links = cursor.fetchone()[0]

            active_links = max(0, total_links - deleted_links - expired_links)

            return AggregateStats(
                total_links=total_links,
                active_links=active_links,
                expired_links=expired_links,
                deleted_links=deleted_links,
                total_hits=total_hits,
            )

    def close(self) -> None:
        """Closes the underlying database connection."""
        with self._lock:
            self._conn.close()
