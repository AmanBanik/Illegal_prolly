import sys
from datetime import datetime, timezone
from pathlib import Path
import pytest

# Ensure workspace root is in sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from Proj_15.src.models import User
from Proj_15.src.service import PasswordResetService
from Proj_15.src.storage import InMemoryDatabase
from Proj_15.src.utils import hash_password


@pytest.fixture
def storage():
    db = InMemoryDatabase()
    now = datetime(2026, 10, 20, 12, 0, 0, tzinfo=timezone.utc)
    user1 = User(
        user_id="usr_001",
        email="alice@example.com",
        password_hash=hash_password("OldPassword123!"),
        created_at=now,
        updated_at=now,
    )
    user2 = User(
        user_id="usr_002",
        email="bob@example.com",
        password_hash=hash_password("SecretPass456!"),
        created_at=now,
        updated_at=now,
    )
    db.save_user(user1)
    db.save_user(user2)
    return db


@pytest.fixture
def service(storage):
    return PasswordResetService(storage=storage)
