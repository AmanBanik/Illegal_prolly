import pytest
from Proj_09.src.models import ReturnAssessmentRequest


def test_stateless_idempotence(guard):
    req = {
        "customer_rating": 4.2,
        "purchase_value": 250.0,
        "account_age_days": 180,
        "request_id": "req_100",
    }

    res1 = guard.assess_return(req)
    res2 = guard.assess_return(req)

    assert res1.total_risk_score == res2.total_risk_score
    assert res1.decision == res2.decision
    assert res1.component_scores == res2.component_scores
    assert res1.reasons == res2.reasons


def test_caller_mutation_isolation(guard):
    metadata = {"tags": ["fragile", "clothing"], "channel": "mobile"}
    req = {
        "customer_rating": 4.0,
        "purchase_value": 75.0,
        "account_age_days": 120,
        "metadata": metadata,
    }

    res1 = guard.assess_return(req)

    # Caller mutates their own metadata dict afterwards
    metadata["tags"].append("hacked")
    metadata["channel"] = "web"

    # Subsequent call with fresh request
    req2 = {
        "customer_rating": 4.0,
        "purchase_value": 75.0,
        "account_age_days": 120,
    }
    res2 = guard.assess_return(req2)

    assert res1.total_risk_score == res2.total_risk_score
    assert res1.decision == res2.decision


def test_immutable_results(guard):
    req = ReturnAssessmentRequest(customer_rating=4.5, purchase_value=100.0, account_age_days=100)
    res = guard.assess_return(req)

    # ReturnAssessmentResult is a frozen dataclass
    with pytest.raises(Exception):
        res.total_risk_score = 999.0

    with pytest.raises(Exception):
        res.decision = "HACKED"
