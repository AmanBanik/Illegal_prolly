from copy import deepcopy
from typing import Any, Dict, Generator, Iterable, List, Optional, Union
from .exceptions import ReturnGuardError, ValidationError
from .models import (
    BatchItemResult,
    ReturnAssessmentRequest,
    ReturnAssessmentResult,
)
from .scorer import RiskScorer


class ReturnGuard:
    """Stateless production pipeline evaluating return risk with strict type safety

    and batch error isolation.
    """

    def __init__(
        self,
        low_risk_threshold: float = 30.0,
        high_risk_threshold: float = 70.0,
    ):
        self._scorer = RiskScorer(
            low_risk_threshold=low_risk_threshold,
            high_risk_threshold=high_risk_threshold,
        )

    def _extract_request_params(
        self,
        request: Union[ReturnAssessmentRequest, Dict[str, Any]],
    ) -> tuple:
        if isinstance(request, ReturnAssessmentRequest):
            return (
                request.customer_rating,
                request.purchase_value,
                request.account_age_days,
                request.request_id,
                deepcopy(request.metadata) if request.metadata else None,
            )
        elif isinstance(request, dict):
            if "customer_rating" not in request:
                raise ValidationError("Missing required field 'customer_rating'")
            if "purchase_value" not in request:
                raise ValidationError("Missing required field 'purchase_value'")
            if "account_age_days" not in request:
                raise ValidationError("Missing required field 'account_age_days'")

            return (
                request.get("customer_rating"),
                request.get("purchase_value"),
                request.get("account_age_days"),
                request.get("request_id"),
                deepcopy(request.get("metadata")),
            )
        else:
            raise ValidationError(
                f"Expected ReturnAssessmentRequest or dict, got {type(request).__name__}"
            )

    def assess_return(
        self,
        request: Union[ReturnAssessmentRequest, Dict[str, Any]],
    ) -> ReturnAssessmentResult:
        """Assesses a single return request with strict validation and deterministic scoring."""
        raw_rating, raw_value, raw_age, request_id, _ = self._extract_request_params(request)

        rating, value, age = self._scorer.validate_inputs(raw_rating, raw_value, raw_age)
        components, total_score, decision, reasons = self._scorer.calculate_scores(
            customer_rating=rating,
            purchase_value=value,
            account_age_days=age,
        )

        return ReturnAssessmentResult(
            request_id=request_id,
            total_risk_score=total_score,
            decision=decision,
            component_scores=components,
            reasons=reasons,
        )

    def stream_assess_batch(
        self,
        requests: Iterable[Union[ReturnAssessmentRequest, Dict[str, Any]]],
    ) -> Generator[BatchItemResult, None, None]:
        """Lazily evaluates an iterable stream of requests, yielding isolated results

        in strict sequence order.
        """
        if requests is None:
            raise ValidationError("requests iterable cannot be None")

        for idx, req in enumerate(requests):
            try:
                res = self.assess_return(req)
                yield BatchItemResult(
                    index=idx,
                    success=True,
                    data=res,
                    error=None,
                )
            except Exception as e:
                yield BatchItemResult(
                    index=idx,
                    success=False,
                    data=None,
                    error=str(e),
                )

    def assess_batch(
        self,
        requests: Iterable[Union[ReturnAssessmentRequest, Dict[str, Any]]],
    ) -> List[BatchItemResult]:
        """Evaluates a batch of return requests with complete failure isolation

        and preserved sequence ordering.
        """
        return list(self.stream_assess_batch(requests))
