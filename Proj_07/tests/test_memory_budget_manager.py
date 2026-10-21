import threading
import time
import pytest
from Proj_07.src.exceptions import MemoryBudgetExceededError
from Proj_07.src.memory_manager import MemoryBudgetManager


def test_acquire_and_release():
    mgr = MemoryBudgetManager(max_memory_bytes=1000)
    assert mgr.available_memory_bytes == 1000

    mgr.acquire(400)
    assert mgr.current_memory_bytes == 400
    assert mgr.available_memory_bytes == 600

    mgr.acquire(300)
    assert mgr.current_memory_bytes == 700

    mgr.release(400)
    assert mgr.current_memory_bytes == 300
    assert mgr.available_memory_bytes == 700


def test_exceed_total_budget_raises_immediately():
    mgr = MemoryBudgetManager(max_memory_bytes=500)
    with pytest.raises(MemoryBudgetExceededError):
        mgr.acquire(501)


def test_blocking_until_memory_released():
    mgr = MemoryBudgetManager(max_memory_bytes=1000)
    mgr.acquire(800)

    acquired_flag = False

    def waiter():
        nonlocal acquired_flag
        mgr.acquire(300)  # Blocks because 800 + 300 = 1100 > 1000
        acquired_flag = True

    t = threading.Thread(target=waiter, daemon=True)
    t.start()
    time.sleep(0.05)
    assert acquired_flag is False

    # Releasing 200 is still not enough (600 + 300 = 900 <= 1000) -> Wait, 800 - 200 = 600.
    # 600 + 300 = 900 <= 1000, so it will unblock!
    mgr.release(200)
    t.join(timeout=1.0)
    assert acquired_flag is True
    assert mgr.current_memory_bytes == 900


def test_peak_memory_tracking():
    mgr = MemoryBudgetManager(max_memory_bytes=2000)
    mgr.acquire(500)
    mgr.acquire(700)
    assert mgr.peak_memory_bytes == 1200
    mgr.release(800)
    assert mgr.current_memory_bytes == 400
    assert mgr.peak_memory_bytes == 1200  # Peak is retained
