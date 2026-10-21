import threading
from typing import Optional
from .exceptions import MemoryBudgetExceededError


class MemoryBudgetManager:
    """Thread-safe manager for tracking and budgeting in-flight memory usage.

    Enforces that concurrent image processing never exceeds the defined memory budget,
    blocking admission of new jobs until sufficient memory is released by completed jobs.
    """

    def __init__(self, max_memory_bytes: int):
        if max_memory_bytes <= 0:
            raise ValueError(f"max_memory_bytes must be positive, got {max_memory_bytes}")
        self._max_memory_bytes = max_memory_bytes
        self._current_memory_bytes = 0
        self._peak_memory_bytes = 0
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)

    @property
    def max_memory_bytes(self) -> int:
        return self._max_memory_bytes

    @property
    def current_memory_bytes(self) -> int:
        with self._lock:
            return self._current_memory_bytes

    @property
    def peak_memory_bytes(self) -> int:
        with self._lock:
            return self._peak_memory_bytes

    @property
    def available_memory_bytes(self) -> int:
        with self._lock:
            return max(0, self._max_memory_bytes - self._current_memory_bytes)

    def acquire(self, size_bytes: int, timeout: Optional[float] = None) -> None:
        """Blocks until `size_bytes` can be allocated within the memory budget.

        Raises:
            MemoryBudgetExceededError: if `size_bytes` is strictly greater than total budget.
            TimeoutError: if timeout is specified and expires before allocation.
        """
        if size_bytes <= 0:
            return

        if size_bytes > self._max_memory_bytes:
            raise MemoryBudgetExceededError(
                f"Image size {size_bytes} bytes exceeds total memory budget {self._max_memory_bytes} bytes"
            )

        with self._condition:
            while self._current_memory_bytes + size_bytes > self._max_memory_bytes:
                signaled = self._condition.wait(timeout=timeout)
                if timeout is not None and not signaled:
                    raise TimeoutError(f"Timed out waiting for {size_bytes} bytes of memory")

            self._current_memory_bytes += size_bytes
            if self._current_memory_bytes > self._peak_memory_bytes:
                self._peak_memory_bytes = self._current_memory_bytes

    def release(self, size_bytes: int) -> None:
        """Releases `size_bytes` back to the pool and notifies waiting threads."""
        if size_bytes <= 0:
            return

        with self._condition:
            self._current_memory_bytes = max(0, self._current_memory_bytes - size_bytes)
            self._condition.notify_all()
