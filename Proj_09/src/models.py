from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class RiskDecision(str, Enum):
    LOW_RISK = "LOW_RISK"
    MEDIUM_RISK = "MEDIUM_RISK"
    HIGH_RISK = "HIGH_RISK"


@dataclass(frozen=True)
class RiskComponentScores:
    """Breakdown of individual risk sub-scores."""
    rating_score: float
    purchase_value_score: float
    account_age_score: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "rating_score": self.rating_score,
            "purchase_value_score": self.purchase_value_score,
            "account_age_score": self.account_age_score,
        }


@dataclass(frozen=True)
class ReturnAssessmentRequest:
    """Immutable input request for assessing return risk."""
    customer_rating: float
    purchase_value: float
    account_age_days: int
    request_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class ReturnAssessmentResult:
    """Immutable assessment decision and score breakdown."""
    total_risk_score: float
    decision: RiskDecision
    component_scores: RiskComponentScores
    reasons: List[str] = field(default_factory=list)
    request_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "total_risk_score": self.total_risk_score,
            "decision": self.decision.value,
            "component_scores": self.component_scores.to_dict(),
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class BatchItemResult:
    """Encapsulates outcome for a single item within a batch, providing error isolation."""
    index: int
    success: bool
    data: Optional[ReturnAssessmentResult] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "success": self.success,
            "data": self.data.to_dict() if self.data else None,
            "error": self.error,
        }
