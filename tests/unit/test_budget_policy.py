from decimal import Decimal

from app.policies.budget_policy import is_over_budget


def test_under_limit_is_not_exceeded() -> None:
    assert is_over_budget(Decimal("1.00"), 2.00) is False


def test_at_limit_is_exceeded() -> None:
    assert is_over_budget(Decimal("2.00"), 2.00) is True


def test_over_limit_is_exceeded() -> None:
    assert is_over_budget(Decimal("2.01"), 2.00) is True


def test_zero_spend_against_positive_limit_is_not_exceeded() -> None:
    assert is_over_budget(Decimal("0"), 2.00) is False
