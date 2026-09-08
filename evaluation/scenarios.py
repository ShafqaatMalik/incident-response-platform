from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

from app.models.incident import Severity

CATEGORIES = (
    "api_failure",
    "auth_failure",
    "dependency_failure",
    "database_problem",
    "deployment_failure",
    "latency_problem",
)

Category = Literal[
    "api_failure",
    "auth_failure",
    "dependency_failure",
    "database_problem",
    "deployment_failure",
    "latency_problem",
]


class ExpectedOutcome(BaseModel):
    severity: Severity
    root_cause: str | None = None
    proposed_action: str | None = None
    should_escalate: bool
    notes: str | None = None


class Scenario(BaseModel):
    id: str
    category: Category
    trigger: str
    initial_evidence: list[str] = Field(default_factory=list)
    expected: ExpectedOutcome


class ScenarioSetValidationError(Exception):
    pass


def load_scenarios(path: Path) -> list[Scenario]:
    raw = yaml.safe_load(path.read_text())
    if not isinstance(raw, list):
        raise ScenarioSetValidationError(f"{path} must contain a YAML list of scenarios.")
    return [Scenario.model_validate(entry) for entry in raw]


def validate_scenario_set(
    scenarios: list[Scenario], *, expected_total: int = 18, expected_per_category: int = 3
) -> None:
    if len(scenarios) != expected_total:
        raise ScenarioSetValidationError(
            f"Expected {expected_total} scenarios, got {len(scenarios)}."
        )

    ids = [s.id for s in scenarios]
    if len(set(ids)) != len(ids):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        raise ScenarioSetValidationError(f"Duplicate scenario ids: {dupes}")

    counts: dict[str, int] = {}
    for scenario in scenarios:
        counts[scenario.category] = counts.get(scenario.category, 0) + 1

    missing = [c for c in CATEGORIES if c not in counts]
    if missing:
        raise ScenarioSetValidationError(f"Missing categories entirely: {missing}")

    wrong = {c: n for c, n in counts.items() if n != expected_per_category}
    if wrong:
        raise ScenarioSetValidationError(
            f"Expected {expected_per_category} scenarios per category, got: {wrong}"
        )
