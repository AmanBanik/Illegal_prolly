import pytest
from Proj_09.src.service import ReturnGuard


@pytest.fixture
def guard():
    """Provides a default ReturnGuard service instance."""
    return ReturnGuard(low_risk_threshold=30.0, high_risk_threshold=70.0)
