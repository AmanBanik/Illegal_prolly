from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from .exceptions import (
    MovieNotFoundError,
    UnauthorizedError,
    ValidationError,
    WatchlistNotFoundError,
)
from .models import MovieItem, Watchlist
from .repository import WatchlistRepository


class ScreenShelf:
    """Production-grade watchlist management service enforcing private ownership,

    strict movie membership isolation, and transactional commits.
    """

    def __init__(
        self,
        db_path: str = ":memory:",
        repository: Optional[WatchlistRepository] = None,
    ):
        self._repo = repository or WatchlistRepository(db_path=db_path)

    @property
    def repository(self) -> WatchlistRepository:
        return self._repo

    def _validate_non_empty_str(self, value: Optional[str], field_name: str, max_length: int = 255) -> str:
        if value is None or not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a non-empty string")
        cleaned = value.strip()
        if not cleaned:
            raise ValidationError(f"{field_name} cannot be empty or whitespace only")
        if len(cleaned) > max_length:
            raise ValidationError(f"{field_name} exceeds maximum length of {max_length} characters")
        return cleaned

    def _validate_id(self, val: Any, name: str) -> int:
        if not isinstance(val, int) or val <= 0:
            raise ValidationError(f"{name} must be a positive integer")
        return val

    def _get_and_authorize(self, watchlist_id: int, user_id: str) -> Dict[str, Any]:
        valid_id = self._validate_id(watchlist_id, "watchlist_id")
        valid_user = self._validate_non_empty_str(user_id, "user_id")

        record = self._repo.get_watchlist_record(valid_id)
        if record is None:
            raise WatchlistNotFoundError(f"Watchlist #{valid_id} does not exist")

        if record["user_id"] != valid_user:
            raise UnauthorizedError(
                f"User '{valid_user}' is not authorized to access private watchlist #{valid_id}"
            )
        return record

    def _build_watchlist_model(self, record: Dict[str, Any]) -> Watchlist:
        created_at = datetime.fromisoformat(record["created_at"])
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        updated_at = datetime.fromisoformat(record["updated_at"])
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)

        movies = self._repo.get_movies_for_watchlist(record["id"])

        return Watchlist(
            id=record["id"],
            user_id=record["user_id"],
            name=record["name"],
            description=record["description"],
            created_at=created_at,
            updated_at=updated_at,
            movies=movies,
        )

    def create_watchlist(
        self,
        user_id: str,
        name: str,
        description: Optional[str] = None,
        current_time: Optional[datetime] = None,
    ) -> Watchlist:
        """Creates a private watchlist for a user and commits immediately."""
        valid_user = self._validate_non_empty_str(user_id, "user_id")
        valid_name = self._validate_non_empty_str(name, "name")

        clean_desc = None
        if description is not None:
            clean_desc = str(description).strip() or None

        now = current_time or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        wid = self._repo.create_watchlist(
            user_id=valid_user,
            name=valid_name,
            description=clean_desc,
            now=now,
        )

        record = self._repo.get_watchlist_record(wid)
        return self._build_watchlist_model(record)

    def get_watchlist(self, watchlist_id: int, user_id: str) -> Watchlist:
        """Fetches a private watchlist with its movies, enforcing user authorization."""
        record = self._get_and_authorize(watchlist_id, user_id)
        return self._build_watchlist_model(record)

    def list_watchlists(self, user_id: str) -> List[Watchlist]:
        """Lists all watchlists belonging to a user (private to caller)."""
        valid_user = self._validate_non_empty_str(user_id, "user_id")
        records = self._repo.list_watchlist_records_for_user(valid_user)
        return [self._build_watchlist_model(r) for r in records]

    def rename_watchlist(
        self,
        watchlist_id: int,
        user_id: str,
        new_name: str,
        current_time: Optional[datetime] = None,
    ) -> Watchlist:
        """Renames an existing watchlist if the user is authorized."""
        valid_name = self._validate_non_empty_str(new_name, "new_name")
        self._get_and_authorize(watchlist_id, user_id)

        now = current_time or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        self._repo.rename_watchlist(watchlist_id, valid_name, now)
        record = self._repo.get_watchlist_record(watchlist_id)
        return self._build_watchlist_model(record)

    def delete_watchlist(self, watchlist_id: int, user_id: str) -> bool:
        """Deletes a watchlist and all its movie associations, enforcing authorization."""
        self._get_and_authorize(watchlist_id, user_id)
        return self._repo.delete_watchlist(watchlist_id)

    def add_movie(
        self,
        watchlist_id: int,
        user_id: str,
        movie_id: str,
        title: str,
        metadata: Optional[Dict[str, Any]] = None,
        current_time: Optional[datetime] = None,
    ) -> MovieItem:
        """Adds a movie to a private watchlist.

        Raises:
            UnauthorizedError: if the user does not own the watchlist.
            DuplicateMovieError: if the movie is already present in this watchlist.
        """
        self._get_and_authorize(watchlist_id, user_id)
        valid_movie_id = self._validate_non_empty_str(movie_id, "movie_id", max_length=100)
        valid_title = self._validate_non_empty_str(title, "title", max_length=500)

        now = current_time or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        self._repo.add_movie(
            watchlist_id=watchlist_id,
            movie_id=valid_movie_id,
            title=valid_title,
            added_at=now,
            metadata=metadata,
        )

        return MovieItem(
            movie_id=valid_movie_id,
            title=valid_title,
            added_at=now,
            metadata=metadata,
        )

    def remove_movie(self, watchlist_id: int, user_id: str, movie_id: str) -> bool:
        """Removes a movie strictly from the specified watchlist.

        Raises:
            UnauthorizedError: if the user does not own the watchlist.
            MovieNotFoundError: if the movie does not belong to this watchlist.
        """
        self._get_and_authorize(watchlist_id, user_id)
        valid_movie_id = self._validate_non_empty_str(movie_id, "movie_id", max_length=100)

        removed = self._repo.remove_movie(watchlist_id, valid_movie_id)
        if not removed:
            raise MovieNotFoundError(
                f"Movie '{valid_movie_id}' not found in watchlist #{watchlist_id}"
            )
        return True

    def get_watchlist_movies(self, watchlist_id: int, user_id: str) -> List[MovieItem]:
        """Returns detached movie list for an authorized user."""
        self._get_and_authorize(watchlist_id, user_id)
        return self._repo.get_movies_for_watchlist(watchlist_id)

    def close(self) -> None:
        """Releases underlying database resources."""
        self._repo.close()


# Alias for flexible test imports
WatchlistService = ScreenShelf
