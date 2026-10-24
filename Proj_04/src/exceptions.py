"""Domain exceptions for SlotWise Reservation Service."""


class SlotWiseError(Exception):
    """Base exception for all SlotWise reservation service errors."""
    pass


class SessionNotFoundError(SlotWiseError):
    """Raised when a requested session is not found."""
    pass


class ReservationNotFoundError(SlotWiseError):
    """Raised when a requested reservation is not found."""
    pass


class CapacityExceededError(SlotWiseError):
    """Raised when attempting to reserve a place in a session that has zero remaining capacity."""
    pass


class DuplicateReservationError(SlotWiseError):
    """Raised when a user attempts to make multiple active reservations for the same session."""
    pass


class UnauthorizedCancellationError(SlotWiseError):
    """Raised when a user attempts to cancel a reservation belonging to another user."""
    pass


class AlreadyCancelledError(SlotWiseError):
    """Raised when attempting to cancel a reservation that is already cancelled."""
    pass


class ValidationError(SlotWiseError):
    """Raised when input parameters fail domain validation rules."""
    pass


class DatabaseRepairError(SlotWiseError):
    """Raised when an in-place database repair fails or detects irreconcilable corruption."""
    pass
