class WatchlistServiceError(Exception):
    """Base exception for ScreenShelf watchlist management service."""
    status_code: int = 500

    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code


class ValidationError(WatchlistServiceError):
    """Raised when input parameters fail validation constraints."""
    status_code: int = 400


class UnauthorizedError(WatchlistServiceError):
    """Raised when an operation violates watchlist ownership (private access)."""
    status_code: int = 403


class WatchlistNotFoundError(WatchlistServiceError):
    """Raised when the specified watchlist does not exist."""
    status_code: int = 404


class MovieNotFoundError(WatchlistServiceError):
    """Raised when a movie is not found in the specified watchlist."""
    status_code: int = 404


class DuplicateMovieError(WatchlistServiceError):
    """Raised when attempting to add a movie that already exists in the target watchlist."""
    status_code: int = 409
