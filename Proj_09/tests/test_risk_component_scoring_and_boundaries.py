import pytest
from Proj_09.src.models import ReturnAssessmentRequest


def test_customer_rating_boundary_tiers(guard):
    # Tier 1: rating >= 4.5 -> 0.0 pts
    r1 = guard.assess_return(ReturnAssessmentRequest(5.0, 10.0, 400))
    assert r1.component_scores.rating_score == 0.0

    r2 = guard.assess_return(ReturnAssessmentRequest(4.5, 10.0, 400))
    assert r2.component_scores.rating_score == 0.0

    # Tier 2: 3.5 <= rating < 4.5 -> 10.0 pts
    r3 = guard.assess_return(ReturnAssessmentRequest(4.49, 10.0, 400))
    assert r3.component_scores.rating_score == 10.0

    r4 = guard.assess_return(ReturnAssessmentRequest(3.5, 10.0, 400))
    assert r4.component_scores.rating_score == 10.0

    # Tier 3: 2.5 <= rating < 3.5 -> 25.0 pts
    r5 = guard.assess_return(ReturnAssessmentRequest(3.49, 10.0, 400))
    assert r5.component_scores.rating_score == 25.0

    r6 = guard.assess_return(ReturnAssessmentRequest(2.5, 10.0, 400))
    assert r6.component_scores.rating_score == 25.0

    # Tier 4: rating < 2.5 -> 40.0 pts
    r7 = guard.assess_return(ReturnAssessmentRequest(2.49, 10.0, 400))
    assert r7.component_scores.rating_score == 40.0

    r8 = guard.assess_return(ReturnAssessmentRequest(0.0, 10.0, 400))
    assert r8.component_scores.rating_score == 40.0


def test_purchase_value_boundary_tiers(guard):
    # Tier 1: value < 50.0 -> 5.0 pts
    v1 = guard.assess_return(ReturnAssessmentRequest(5.0, 0.0, 400))
    assert v1.component_scores.purchase_value_score == 5.0

    v2 = guard.assess_return(ReturnAssessmentRequest(5.0, 49.99, 400))
    assert v2.component_scores.purchase_value_score == 5.0

    # Tier 2: 50.0 <= value < 200.0 -> 15.0 pts
    v3 = guard.assess_return(ReturnAssessmentRequest(5.0, 50.0, 400))
    assert v3.component_scores.purchase_value_score == 15.0

    v4 = guard.assess_return(ReturnAssessmentRequest(5.0, 199.99, 400))
    assert v4.component_scores.purchase_value_score == 15.0

    # Tier 3: 200.0 <= value < 1000.0 -> 25.0 pts
    v5 = guard.assess_return(ReturnAssessmentRequest(5.0, 200.0, 400))
    assert v5.component_scores.purchase_value_score == 25.0

    v6 = guard.assess_return(ReturnAssessmentRequest(5.0, 999.99, 400))
    assert v6.component_scores.purchase_value_score == 25.0

    # Tier 4: value >= 1000.0 -> 35.0 pts
    v7 = guard.assess_return(ReturnAssessmentRequest(5.0, 1000.0, 400))
    assert v7.component_scores.purchase_value_score == 35.0

    v8 = guard.assess_return(ReturnAssessmentRequest(5.0, 50000.0, 400))
    assert v8.component_scores.purchase_value_score == 35.0


def test_account_age_boundary_tiers(guard):
    # Tier 1: age >= 365 days -> 0.0 pts
    a1 = guard.assess_return(ReturnAssessmentRequest(5.0, 10.0, 365))
    assert a1.component_scores.account_age_score == 0.0

    a2 = guard.assess_return(ReturnAssessmentRequest(5.0, 10.0, 1000))
    assert a2.component_scores.account_age_score == 0.0

    # Tier 2: 90 <= age < 365 -> 5.0 pts
    a3 = guard.assess_return(ReturnAssessmentRequest(5.0, 10.0, 364))
    assert a3.component_scores.account_age_score == 5.0

    a4 = guard.assess_return(ReturnAssessmentRequest(5.0, 10.0, 90))
    assert a4.component_scores.account_age_score == 5.0

    # Tier 3: 30 <= age < 90 -> 15.0 pts
    a5 = guard.assess_return(ReturnAssessmentRequest(5.0, 10.0, 89))
    assert a5.component_scores.account_age_score == 15.0

    a6 = guard.assess_return(ReturnAssessmentRequest(5.0, 10.0, 30))
    assert a6.component_scores.account_age_score == 15.0

    # Tier 4: age < 30 -> 25.0 pts
    a7 = guard.assess_return(ReturnAssessmentRequest(5.0, 10.0, 29))
    assert a7.component_scores.account_age_score == 25.0

    a8 = guard.assess_return(ReturnAssessmentRequest(5.0, 10.0, 0))
    assert a8.component_scores.account_age_score == 25.0
