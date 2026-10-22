import concurrent.futures
from Proj_09.src.models import ReturnAssessmentRequest, RiskDecision


def test_concurrent_risk_assessments(guard):
    """Verify that multiple concurrent threads assessing return risk operate in complete isolation

    without cross-talk or race conditions.
    """
    num_threads = 50

    def assess_task(i: int):
        # Even i: high risk; Odd i: low risk
        if i % 2 == 0:
            req = ReturnAssessmentRequest(
                customer_rating=1.5,
                purchase_value=1200.0,
                account_age_days=10,
                request_id=f"req_{i}",
            )
            expected_decision = RiskDecision.HIGH_RISK
        else:
            req = ReturnAssessmentRequest(
                customer_rating=4.8,
                purchase_value=25.0,
                account_age_days=400,
                request_id=f"req_{i}",
            )
            expected_decision = RiskDecision.LOW_RISK

        res = guard.assess_return(req)
        return i, res, expected_decision

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(assess_task, i) for i in range(num_threads)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(results) == num_threads

    for i, res, expected_decision in results:
        assert res.request_id == f"req_{i}"
        assert res.decision == expected_decision
