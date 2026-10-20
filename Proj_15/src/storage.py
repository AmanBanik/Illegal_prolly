import copy
import threading
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional
from .models import ResetCodeRecord, User


class StorageBoundary(ABC):
    """Abstract interface defining the database persistence boundary."""

    @abstractmethod
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        pass

    @abstractmethod
    def get_user_by_email(self, email: str) -> Optional[User]:
        pass

    @abstractmethod
    def save_user(self, user: User) -> None:
        pass

    @abstractmethod
    def update_user_password(self, user_id: str, new_password_hash: str, updated_at: datetime) -> bool:
        pass

    @abstractmethod
    def save_reset_code(self, record: ResetCodeRecord) -> None:
        pass

    @abstractmethod
    def get_latest_reset_code(self, user_id: str) -> Optional[ResetCodeRecord]:
        pass

    @abstractmethod
    def get_reset_code(self, user_id: str, code: str) -> Optional[ResetCodeRecord]:
        pass

    @abstractmethod
    def mark_code_used(self, user_id: str, code: str) -> bool:
        pass

    @abstractmethod
    def revoke_all_codes_for_user(self, user_id: str) -> None:
        pass

    @abstractmethod
    def increment_failed_attempts(self, user_id: str, code: str) -> int:
        pass


class InMemoryDatabase(StorageBoundary):
    """Thread-safe in-memory database implementation of the StorageBoundary.

    Guarantees:
    - Thread-safety across concurrent service instances and worker threads.
    - Defensive snapshot copying to protect data encapsulation.
    - Atomic password updates and one-time token consumption.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._users_by_id: Dict[str, User] = {}
        self._users_by_email: Dict[str, str] = {}  # email -> user_id
        # user_id -> List[ResetCodeRecord]
        self._reset_codes: Dict[str, List[ResetCodeRecord]] = {}

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        with self._lock:
            user = self._users_by_id.get(user_id)
            return copy.deepcopy(user) if user else None

    def get_user_by_email(self, email: str) -> Optional[User]:
        with self._lock:
            uid = self._users_by_email.get(email.strip().lower())
            if not uid:
                return None
            user = self._users_by_id.get(uid)
            return copy.deepcopy(user) if user else None

    def save_user(self, user: User) -> None:
        with self._lock:
            stored_user = copy.deepcopy(user)
            self._users_by_id[user.user_id] = stored_user
            self._users_by_email[user.email.strip().lower()] = user.user_id

    def update_user_password(self, user_id: str, new_password_hash: str, updated_at: datetime) -> bool:
        with self._lock:
            user = self._users_by_id.get(user_id)
            if not user:
                return False
            user.password_hash = new_password_hash
            user.updated_at = updated_at
            return True

    def save_reset_code(self, record: ResetCodeRecord) -> None:
        with self._lock:
            if record.user_id not in self._reset_codes:
                self._reset_codes[record.user_id] = []
            self._reset_codes[record.user_id].append(copy.deepcopy(record))

    def get_latest_reset_code(self, user_id: str) -> Optional[ResetCodeRecord]:
        with self._lock:
            codes = self._reset_codes.get(user_id, [])
            if not codes:
                return None
            return copy.deepcopy(codes[-1])

    def get_reset_code(self, user_id: str, code: str) -> Optional[ResetCodeRecord]:
        with self._lock:
            codes = self._reset_codes.get(user_id, [])
            for c in reversed(codes):
                if c.code == code:
                    return copy.deepcopy(c)
            return None

    def mark_code_used(self, user_id: str, code: str) -> bool:
        """Atomically marks a code as used. Returns True if successfully marked, False if already used or missing."""
        with self._lock:
            codes = self._reset_codes.get(user_id, [])
            for c in reversed(codes):
                if c.code == code:
                    if c.is_used:
                        return False
                    c.is_used = True
                    return True
            return False

    def revoke_all_codes_for_user(self, user_id: str) -> None:
        with self._lock:
            codes = self._reset_codes.get(user_id, [])
            for c in codes:
                c.is_used = True

    def increment_failed_attempts(self, user_id: str, code: str) -> int:
        with self._lock:
            codes = self._reset_codes.get(user_id, [])
            for c in reversed(codes):
                if c.code == code:
                    c.failed_attempts += 1
                    return c.failed_attempts
            return 0
