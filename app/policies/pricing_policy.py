from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ModelPricing:
    input_price_per_token: Decimal
    output_price_per_token: Decimal


# Verified against platform.claude.com/docs/en/about-claude/pricing (2026-09-01),
# base input-token rate (no prompt-caching multipliers applied here). Re-check
# periodically -- this is a snapshot, not a guarantee it stays current.
MODEL_PRICING: dict[str, ModelPricing] = {
    "claude-sonnet-5": ModelPricing(Decimal("0.000002"), Decimal("0.00001")),
    "claude-opus-5": ModelPricing(Decimal("0.000005"), Decimal("0.000025")),
    "claude-haiku-4-5-20251001": ModelPricing(Decimal("0.000001"), Decimal("0.000005")),
}


class UnknownModelPricingError(Exception):
    pass


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> Decimal:
    if model not in MODEL_PRICING:
        raise UnknownModelPricingError(f"No fixed pricing entry for model '{model}'.")
    pricing = MODEL_PRICING[model]
    return (
        input_tokens * pricing.input_price_per_token
        + output_tokens * pricing.output_price_per_token
    )
