"""Domain models and data structures for SlotWise Reservation Service."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ReservationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class Session:
    session_id: str
    title: str
    total_capacity: int
    remaining_capacity: int
    start_time: str
    end_time: str
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "title": self.title,
            "total_capacity": self.total_capacity,
            "remaining_capacity": self.remaining_capacity,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class Reservation:
    reservation_id: str
    session_id: str
    user_id: str
    status: ReservationStatus
    created_at: str
    cancelled_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reservation_id": self.reservation_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "status": self.status.value,
            "created_at": self.created_at,
            "cancelled_at": self.cancelled_at,
        }


@dataclass(frozen=True)
class SessionCapacityReport:
    session_id: str
    title: str
    total_capacity: int
    active_reservations: int
    cancelled_reservations: int
    remaining_capacity: int
    is_consistent: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "title": self.title,
            "total_capacity": self.total_capacity,
            "active_reservations": self.active_reservations,
            "cancelled_reservations": self.cancelled_reservations,
            "remaining_capacity": self.remaining_capacity,
            "is_consistent": self.is_consistent,
        }


@dataclass
class RepairReport:
    timestamp: str
    dry_run: bool
    total_sessions_checked: int = 0
    sessions_repaired: int = 0
    overbooked_sessions_fixed: int = 0
    desynced_capacity_fixed: int = 0
    corrupted_reservations_fixed: int = 0
    orphaned_reservations_cleaned: int = 0
    details: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "dry_run": self.dry_run,
            "total_sessions_checked": self.total_sessions_checked,
            "sessions_repaired": self.sessions_repaired,
            "overbooked_sessions_fixed": self.overbooked_sessions_fixed,
            "desynced_capacity_fixed": self.desynced_capacity_fixed,
            "corrupted_reservations_fixed": self.corrupted_reservations_fixed,
            "orphaned_reservations_cleaned": self.orphaned_reservations_cleaned,
            "details": list(self.details),
        }
