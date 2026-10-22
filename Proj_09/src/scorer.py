import math
from typing import Any, List, Tuple
from .exceptions import (
    InvalidAccountAgeError,
    InvalidPurchaseValueError,
    InvalidRatingError,
)
from .models import RiskComponentScores, RiskDecision


class RiskScorer:
    """Deterministic, stateless calculator for return risk assessment."""

    def __init__(
        self,
        low_risk_threshold: float = 30.0,
        high_risk_threshold: float = 70.0,
    ):
        if low_risk_threshold >= high_risk_threshold:
            raise ValueError("low_risk_threshold must be strictly less than high_risk_threshold")
        self._low_threshold = low_risk_threshold
        self._high_threshold = high_risk_threshold

    def validate_inputs(
        self,
        customer_rating: Any,
        purchase_value: Any,
        account_age_days: Any,
    ) -> Tuple[float, float, int]:
        """Strictly validates types and boundary ranges.

        Enforces:
        - Booleans are rejected (not treated as 0 or 1 integers).
        - customer_rating: numeric in [0.0, 5.0], finite.
        - purchase_value: numeric >= 0.0, finite.
        - account_age_days: integer >= 0.
        """
        # 1. Rating validation
        if isinstance(customer_rating, bool):
            raise InvalidRatingError("customer_rating cannot be a boolean value")
        if not isinstance(customer_rating, (int, float)):
            raise InvalidRatingError(
                f"customer_rating must be a numeric value, got {type(customer_rating).__name__}"
            )
        if not math.isfinite(customer_rating):
            raise InvalidRatingError("customer_rating must be a finite number")
        if not (0.0 <= customer_rating <= 5.0):
            raise InvalidRatingError(
                f"customer_rating must be between 0.0 and 5.0, got {customer_rating}"
            )

        # 2. Purchase value validation
        if isinstance(purchase_value, bool):
            raise InvalidPurchaseValueError("purchase_value cannot be a boolean value")
        if not isinstance(purchase_value, (int, float)):
            raise InvalidPurchaseValueError(
                f"purchase_value must be a numeric value, got {type(purchase_value).__name__}"
            )
        if not math.isfinite(purchase_value):
            raise InvalidPurchaseValueError("purchase_value must be a finite number")
        if purchase_value < 0.0:
            raise InvalidPurchaseValueError(
                f"purchase_value cannot be negative, got {purchase_value}"
            )

        # 3. Account age validation
        if isinstance(account_age_days, bool):
            raise InvalidAccountAgeError("account_age_days cannot be a boolean value")
        if not isinstance(account_age_days, int):
            raise InvalidAccountAgeError(
                f"account_age_days must be an integer, got {type(account_age_days).__name__}"
            )
        if account_age_days < 0:
            raise InvalidAccountAgeError(
                f"account_age_days cannot be negative, got {account_age_days}"
            )

        return float(customer_rating), float(purchase_value), int(account_age_days)

    def calculate_scores(
        self,
        customer_rating: float,
        purchase_value: float,
        account_age_days: int,
    ) -> Tuple[RiskComponentScores, float, RiskDecision, List[str]]:
        """Calculates tiered component scores, total composite score, and risk decision."""
        reasons: List[str] = []

        # --- 1. Rating Score (Max 40 pts) ---
        if customer_rating >= 4.5:
            rating_score = 0.0
            reasons.append("Excellent customer rating (>= 4.5)")
        elif customer_rating >= 3.5:
            rating_score = 10.0
            reasons.append("Good customer rating (3.5 - 4.4)")
        elif customer_rating >= 2.5:
            rating_score = 25.0
            reasons.append("Average customer rating (2.5 - 3.4)")
        else:
            rating_score = 40.0
            reasons.append("Low customer rating (< 2.5)")

        # --- 2. Purchase Value Score (Max 35 pts) ---
        if purchase_value < 50.0:
            value_score = 5.0
            reasons.append("Low purchase value (< $50)")
        elif purchase_value < 200.0:
            value_score = 15.0
            reasons.append("Standard purchase value ($50 - $199.99)")
        elif purchase_value < 1000.0:
            value_score = 25.0
            reasons.append("High purchase value ($200 - $999.99)")
        else:
            value_score = 35.0
            reasons.append("Luxury/extreme purchase value (>= $1000)")

        # --- 3. Account Age Score (Max 25 pts) ---
        if account_age_days >= 365:
            age_score = 0.0
            reasons.append("Established veteran account (>= 1 year)")
        elif account_age_days >= 90:
            age_score = 5.0
            reasons.append("Established account (90 - 364 days)")
        elif account_age_days >= 30:
            age_score = 15.0
            reasons.append("Maturing account (30 - 89 days)")
        else:
            age_score = 25.0
            reasons.append("New account (< 30 days)")

        # --- Composite Calculation ---
        total_score = round(rating_score + value_score + age_score, 2)
        total_score = max(0.0, min(100.0, total_score))

        # --- Decision Mapping ---
        if total_score < self._low_threshold:
            decision = RiskDecision.LOW_RISK
        elif total_score < self._high_threshold:
            decision = RiskDecision.MEDIUM_RISK
        else:
            decision = RiskDecision.HIGH_RISK

        components = RiskComponentScores(
            rating_score=rating_score,
            purchase_value_score=value_score,
            account_age_score=age_score,
        )

        return components, total_score, decision, reasons
