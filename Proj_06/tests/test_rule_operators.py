"""Targeting rule operator evaluations and edge case type safety tests."""

import pytest

from Proj_06.src.evaluator import evaluate_condition
from Proj_06.src.models import Operator, RuleCondition


def test_equals_and_not_equals_operators() -> None:
    """Verify EQUALS and NOT_EQUALS with strict boolean trap prevention."""
    # String equality
    c_eq_str = RuleCondition("country", Operator.EQUALS, "CA")
    assert evaluate_condition(c_eq_str, {"country": "CA"}) is True
    assert evaluate_condition(c_eq_str, {"country": "US"}) is False

    # Numeric equality
    c_eq_num = RuleCondition("score", Operator.EQUALS, 100)
    assert evaluate_condition(c_eq_num, {"score": 100}) is True
    assert evaluate_condition(c_eq_num, {"score": 100.0}) is True

    # Boolean trap: True != 1, False != 0
    c_eq_bool = RuleCondition("is_active", Operator.EQUALS, True)
    assert evaluate_condition(c_eq_bool, {"is_active": True}) is True
    assert evaluate_condition(c_eq_bool, {"is_active": 1}) is False
    assert evaluate_condition(c_eq_bool, {"is_active": "True"}) is False

    # NOT_EQUALS
    c_neq = RuleCondition("country", Operator.NOT_EQUALS, "CA")
    assert evaluate_condition(c_neq, {"country": "US"}) is True
    assert evaluate_condition(c_neq, {"country": "CA"}) is False


def test_in_and_not_in_operators() -> None:
    """Verify IN and NOT_IN with list membership and boolean isolation."""
    c_in = RuleCondition("role", Operator.IN, ["admin", "editor", "moderator"])
    assert evaluate_condition(c_in, {"role": "editor"}) is True
    assert evaluate_condition(c_in, {"role": "viewer"}) is False

    # Boolean trap in list: 1 should NOT match True in list
    c_in_bool = RuleCondition("flag", Operator.IN, [True])
    assert evaluate_condition(c_in_bool, {"flag": True}) is True
    assert evaluate_condition(c_in_bool, {"flag": 1}) is False

    # NOT_IN
    c_notin = RuleCondition("env", Operator.NOT_IN, ["prod", "production"])
    assert evaluate_condition(c_notin, {"env": "staging"}) is True
    assert evaluate_condition(c_notin, {"env": "prod"}) is False


def test_contains_operator() -> None:
    """Verify CONTAINS for string substrings and list membership."""
    c_contains_str = RuleCondition("email", Operator.CONTAINS, "@corp.")
    assert evaluate_condition(c_contains_str, {"email": "alice@corp.example.com"}) is True
    assert evaluate_condition(c_contains_str, {"email": "alice@gmail.com"}) is False

    c_contains_list = RuleCondition("tags", Operator.CONTAINS, "vip")
    assert evaluate_condition(c_contains_list, {"tags": ["vip", "beta"]}) is True
    assert evaluate_condition(c_contains_list, {"tags": ["standard"]}) is False


def test_starts_with_and_ends_with_operators() -> None:
    """Verify prefix and suffix matching."""
    c_starts = RuleCondition("route", Operator.STARTS_WITH, "/api/v2/")
    assert evaluate_condition(c_starts, {"route": "/api/v2/users"}) is True
    assert evaluate_condition(c_starts, {"route": "/api/v1/users"}) is False

    c_ends = RuleCondition("email", Operator.ENDS_WITH, "@company.com")
    assert evaluate_condition(c_ends, {"email": "dev@company.com"}) is True
    assert evaluate_condition(c_ends, {"email": "dev@external.com"}) is False

    # Safe return False on non-string actual value
    assert evaluate_condition(c_starts, {"route": 12345}) is False


def test_numeric_comparison_operators() -> None:
    """Verify numeric comparisons with float support and boolean rejection."""
    c_gt = RuleCondition("age", Operator.GREATER_THAN, 18)
    assert evaluate_condition(c_gt, {"age": 21}) is True
    assert evaluate_condition(c_gt, {"age": 18}) is False
    assert evaluate_condition(c_gt, {"age": 16}) is False

    c_gte = RuleCondition("version", Operator.GREATER_THAN_OR_EQUAL, 2.5)
    assert evaluate_condition(c_gte, {"version": 2.5}) is True
    assert evaluate_condition(c_gte, {"version": 3.0}) is True
    assert evaluate_condition(c_gte, {"version": 2.49}) is False

    c_lt = RuleCondition("price", Operator.LESS_THAN, 50.0)
    assert evaluate_condition(c_lt, {"price": 49.99}) is True
    assert evaluate_condition(c_lt, {"price": 50.0}) is False

    c_lte = RuleCondition("latency", Operator.LESS_THAN_OR_EQUAL, 200)
    assert evaluate_condition(c_lte, {"latency": 200}) is True
    assert evaluate_condition(c_lte, {"latency": 201}) is False

    # Boolean trap rejection in comparisons: True > 0 must return False
    assert evaluate_condition(c_gt, {"age": True}) is False
    assert evaluate_condition(c_lt, {"price": False}) is False


def test_missing_attribute_handling() -> None:
    """Verify missing attributes fail positive operators and pass negative operators."""
    attrs = {"unrelated": "value"}

    assert evaluate_condition(RuleCondition("missing", Operator.EQUALS, "US"), attrs) is False
    assert evaluate_condition(RuleCondition("missing", Operator.CONTAINS, "a"), attrs) is False
    assert evaluate_condition(RuleCondition("missing", Operator.GREATER_THAN, 10), attrs) is False

    # Negative operators evaluate safely
    assert evaluate_condition(RuleCondition("missing", Operator.NOT_EQUALS, "US"), attrs) is True
    assert evaluate_condition(RuleCondition("missing", Operator.NOT_IN, ["US", "CA"]), attrs) is True
