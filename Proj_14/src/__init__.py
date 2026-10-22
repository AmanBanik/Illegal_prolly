from .app import create_app
from .exceptions import (
    DuplicateMovieError,
    MovieNotFoundError,
    UnauthorizedError,
    ValidationError,
    WatchlistNotFoundError,
    WatchlistServiceError,
)
from .models import MovieItem, Watchlist
from .repository import WatchlistRepository
from .service import ScreenShelf, WatchlistService

__all__ = [
    "ScreenShelf",
    "WatchlistService",
    "WatchlistRepository",
    "Watchlist",
    "MovieItem",
    "create_app",
    "WatchlistServiceError",
    "ValidationError",
    "UnauthorizedError",
    "WatchlistNotFoundError",
    "MovieNotFoundError",
    "DuplicateMovieError",
]
