import pytest
from Proj_09.src.models import ReturnAssessmentRequest, RiskDecision


def test_batch_error_isolation_and_order_preservation(guard):
    """CRITICAL TEST: An invalid item within a batch must be isolated without aborting

    the evaluation of subsequent valid items, and output sequence order must be preserved.
    """
    batch_input = [
        # 0: Valid
        {"customer_rating": 4.8, "purchase_value": 30.0, "account_age_days": 400},
        # 1: Boolean trap error
        {"customer_rating": True, "purchase_value": 100.0, "account_age_days": 50},
        # 2: Valid
        ReturnAssessmentRequest(customer_rating=2.0, purchase_value=1200.0, account_age_days=10),
        # 3: Negative value error
        {"customer_rating": 4.0, "purchase_value": -99.0, "account_age_days": 50},
        # 4: Valid
        {"customer_rating": 3.8, "purchase_value": 150.0, "account_age_days": 120},
        # 5: Missing field error
        {"purchase_value": 150.0, "account_age_days": 120},
    ]

    results = guard.assess_batch(batch_input)

    assert len(results) == 6

    # Verify indices and sequence order
    assert [r.index for r in results] == [0, 1, 2, 3, 4, 5]

    # Item 0: Success
    assert results[0].success is True
    assert results[0].data.decision == RiskDecision.LOW_RISK
    assert results[0].error is None

    # Item 1: Isolated Failure (Boolean trap)
    assert results[1].success is False
    assert results[1].data is None
    assert "cannot be a boolean" in results[1].error

    # Item 2: Success
    assert results[2].success is True
    assert results[2].data.decision == RiskDecision.HIGH_RISK
    assert results[2].error is None

    # Item 3: Isolated Failure (Negative value)
    assert results[3].success is False
    assert results[3].data is None
    assert "cannot be negative" in results[3].error

    # Item 4: Success (Score: 10 + 15 + 5 = 30.0 -> MEDIUM_RISK)
    assert results[4].success is True
    assert results[4].data.decision == RiskDecision.MEDIUM_RISK
    assert results[4].error is None

    # Item 5: Isolated Failure (Missing field)
    assert results[5].success is False
    assert results[5].data is None
    assert "Missing required field" in results[5].error


def test_streaming_generator_single_pass_processing(guard):
    """Verify stream_assess_batch lazily consumes iterables without materializing them all into memory."""
    def lazy_generator():
        for i in range(5):
            yield {"customer_rating": 4.0, "purchase_value": 50.0 + i, "account_age_days": 100}

    gen = guard.stream_assess_batch(lazy_generator())
    consumed = []
    for item in gen:
        assert item.success is True
        consumed.append(item)

    assert len(consumed) == 5
    assert [c.index for c in consumed] == [0, 1, 2, 3, 4]


def test_empty_batch(guard):
    assert guard.assess_batch([]) == []
