import pytest
from Proj_09.src.exceptions import (
    InvalidAccountAgeError,
    InvalidPurchaseValueError,
    InvalidRatingError,
    ValidationError,
)
from Proj_09.src.models import ReturnAssessmentRequest


def test_boolean_trap_in_customer_rating(guard):
    """CRITICAL TEST: In Python, bool is an int subclass (isinstance(True, int) == True).

    Passing boolean True or False must be explicitly rejected with InvalidRatingError.
    """
    with pytest.raises(InvalidRatingError) as exc_info:
        guard.assess_return({"customer_rating": True, "purchase_value": 100.0, "account_age_days": 45})
    assert "cannot be a boolean" in str(exc_info.value)

    with pytest.raises(InvalidRatingError) as exc_info2:
        guard.assess_return(
            ReturnAssessmentRequest(customer_rating=False, purchase_value=100.0, account_age_days=45)
        )
    assert "cannot be a boolean" in str(exc_info2.value)


def test_boolean_trap_in_purchase_value(guard):
    """Passing boolean True or False as purchase value must be rejected."""
    with pytest.raises(InvalidPurchaseValueError) as exc_info:
        guard.assess_return({"customer_rating": 4.5, "purchase_value": True, "account_age_days": 45})
    assert "cannot be a boolean" in str(exc_info.value)

    with pytest.raises(InvalidPurchaseValueError):
        guard.assess_return({"customer_rating": 4.5, "purchase_value": False, "account_age_days": 45})


def test_boolean_trap_in_account_age(guard):
    """Passing boolean True or False as account age must be rejected."""
    with pytest.raises(InvalidAccountAgeError) as exc_info:
        guard.assess_return({"customer_rating": 4.5, "purchase_value": 100.0, "account_age_days": True})
    assert "cannot be a boolean" in str(exc_info.value)

    with pytest.raises(InvalidAccountAgeError):
        guard.assess_return({"customer_rating": 4.5, "purchase_value": 100.0, "account_age_days": False})


def test_rating_boundary_and_range_validation(guard):
    # Rating out of bounds (< 0 or > 5.0)
    with pytest.raises(InvalidRatingError):
        guard.assess_return({"customer_rating": -0.1, "purchase_value": 50.0, "account_age_days": 100})

    with pytest.raises(InvalidRatingError):
        guard.assess_return({"customer_rating": 5.1, "purchase_value": 50.0, "account_age_days": 100})

    # Non-finite values
    with pytest.raises(InvalidRatingError):
        guard.assess_return({"customer_rating": float("nan"), "purchase_value": 50.0, "account_age_days": 100})

    with pytest.raises(InvalidRatingError):
        guard.assess_return({"customer_rating": float("inf"), "purchase_value": 50.0, "account_age_days": 100})

    # Non-numeric string
    with pytest.raises(InvalidRatingError):
        guard.assess_return({"customer_rating": "5.0", "purchase_value": 50.0, "account_age_days": 100})


def test_purchase_value_negative_and_non_finite(guard):
    with pytest.raises(InvalidPurchaseValueError):
        guard.assess_return({"customer_rating": 4.0, "purchase_value": -0.01, "account_age_days": 100})

    with pytest.raises(InvalidPurchaseValueError):
        guard.assess_return({"customer_rating": 4.0, "purchase_value": float("nan"), "account_age_days": 100})

    with pytest.raises(InvalidPurchaseValueError):
        guard.assess_return({"customer_rating": 4.0, "purchase_value": "100", "account_age_days": 100})


def test_account_age_float_and_negative(guard):
    # Account age must be integer, not float
    with pytest.raises(InvalidAccountAgeError):
        guard.assess_return({"customer_rating": 4.0, "purchase_value": 100.0, "account_age_days": 30.5})

    with pytest.raises(InvalidAccountAgeError):
        guard.assess_return({"customer_rating": 4.0, "purchase_value": 100.0, "account_age_days": -1})


def test_missing_fields_and_invalid_container(guard):
    with pytest.raises(ValidationError):
        guard.assess_return({"purchase_value": 100.0, "account_age_days": 30})

    with pytest.raises(ValidationError):
        guard.assess_return("not_a_valid_request")
