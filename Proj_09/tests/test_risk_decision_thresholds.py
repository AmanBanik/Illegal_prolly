import pytest
from Proj_09.src.models import ReturnAssessmentRequest, RiskDecision
from Proj_09.src.service import ReturnGuard


def test_absolute_extremes_minimum_and_maximum(guard):
    # Minimum possible risk: Rating 5.0 (0 pts) + Value $10 (5 pts) + Age 500 days (0 pts) = 5.0 pts -> LOW_RISK
    best_req = ReturnAssessmentRequest(customer_rating=5.0, purchase_value=10.0, account_age_days=500)
    best_res = guard.assess_return(best_req)
    assert best_res.total_risk_score == 5.0
    assert best_res.decision == RiskDecision.LOW_RISK

    # Maximum possible risk: Rating 1.0 (40 pts) + Value $1500 (35 pts) + Age 5 days (25 pts) = 100.0 pts -> HIGH_RISK
    worst_req = ReturnAssessmentRequest(customer_rating=1.0, purchase_value=1500.0, account_age_days=5)
    worst_res = guard.assess_return(worst_req)
    assert worst_res.total_risk_score == 100.0
    assert worst_res.decision == RiskDecision.HIGH_RISK


def test_decision_boundary_thresholds(guard):
    # Rating 4.0 (10 pts) + Value $100 (15 pts) + Age 100 days (5 pts) = 30.0 pts -> Exactly at MEDIUM_RISK boundary!
    req_30 = ReturnAssessmentRequest(customer_rating=4.0, purchase_value=100.0, account_age_days=100)
    res_30 = guard.assess_return(req_30)
    assert res_30.total_risk_score == 30.0
    assert res_30.decision == RiskDecision.MEDIUM_RISK

    # Rating 5.0 (0 pts) + Value $300 (25 pts) + Age 400 days (0 pts) = 25.0 pts -> LOW_RISK
    req_25 = ReturnAssessmentRequest(customer_rating=5.0, purchase_value=300.0, account_age_days=400)
    res_25 = guard.assess_return(req_25)
    assert res_25.total_risk_score == 25.0
    assert res_25.decision == RiskDecision.LOW_RISK

    # Rating 2.0 (40 pts) + Value $300 (25 pts) + Age 100 days (5 pts) = 70.0 pts -> Exactly at HIGH_RISK boundary!
    req_70 = ReturnAssessmentRequest(customer_rating=2.0, purchase_value=300.0, account_age_days=100)
    res_70 = guard.assess_return(req_70)
    assert res_70.total_risk_score == 70.0
    assert res_70.decision == RiskDecision.HIGH_RISK


def test_custom_threshold_configuration():
    strict_guard = ReturnGuard(low_risk_threshold=20.0, high_risk_threshold=50.0)

    # Score of 25.0 would be LOW_RISK under default (30), but is MEDIUM_RISK under strict (20)
    req = ReturnAssessmentRequest(customer_rating=5.0, purchase_value=300.0, account_age_days=400)
    res = strict_guard.assess_return(req)
    assert res.total_risk_score == 25.0
    assert res.decision == RiskDecision.MEDIUM_RISK


def test_invalid_threshold_initialization():
    with pytest.raises(ValueError):
        ReturnGuard(low_risk_threshold=70.0, high_risk_threshold=30.0)

    with pytest.raises(ValueError):
        ReturnGuard(low_risk_threshold=50.0, high_risk_threshold=50.0)
