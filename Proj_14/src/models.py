from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class MovieItem:
    """Detached snapshot of a movie member in a watchlist."""
    movie_id: str
    title: str
    added_at: datetime
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "movie_id": self.movie_id,
            "title": self.title,
            "added_at": self.added_at.isoformat(),
            "metadata": self.metadata or {},
        }


@dataclass(frozen=True)
class Watchlist:
    """Detached snapshot of a user's private watchlist."""
    id: int
    user_id: str
    name: str
    description: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    movies: List[MovieItem] = field(default_factory=list)

    @property
    def movie_count(self) -> int:
        return len(self.movies)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "movie_count": self.movie_count,
            "movies": [m.to_dict() for m in self.movies],
        }
