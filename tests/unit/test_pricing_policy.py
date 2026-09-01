from decimal import Decimal

import pytest

from app.policies.pricing_policy import UnknownModelPricingError, calculate_cost


def test_input_tokens_only() -> None:
    cost = calculate_cost("claude-sonnet-5", input_tokens=1_000_000, output_tokens=0)
    assert cost == Decimal("2")


def test_output_tokens_only() -> None:
    cost = calculate_cost("claude-sonnet-5", input_tokens=0, output_tokens=1_000_000)
    assert cost == Decimal("10")


def test_input_and_output_tokens_combined() -> None:
    cost = calculate_cost("claude-sonnet-5", input_tokens=1_000_000, output_tokens=1_000_000)
    assert cost == Decimal("12")


def test_zero_tokens_is_zero_cost() -> None:
    cost = calculate_cost("claude-sonnet-5", input_tokens=0, output_tokens=0)
    assert cost == Decimal("0")


def test_unknown_model_raises() -> None:
    with pytest.raises(UnknownModelPricingError):
        calculate_cost("not-a-real-model", input_tokens=100, output_tokens=100)
