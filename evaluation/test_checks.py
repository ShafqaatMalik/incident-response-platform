from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from checks import (
    CallRecord,
    check_escalation_correctness,
    check_evidence_present_at_each_stage,
    check_valid_action_type,
    check_validator_not_bypassed,
    cost_for_stage,
    extract_call_records,
    judge_cost,
    latency_ms_by_stage,
    run_rule_based_checks,
    total_incident_cost,
)
from scenarios import (
    ExpectedOutcome,
    Scenario,
    ScenarioSetValidationError,
    load_scenarios,
    validate_scenario_set,
)

from app.models.incident import ActionType, Incident

# --- check_escalation_correctness ---


def test_escalation_correctness_true_when_expected_and_actual_both_escalated() -> None:
    assert check_escalation_correctness(True, "escalated") is True


def test_escalation_correctness_true_when_neither_escalated() -> None:
    assert check_escalation_correctness(False, "awaiting_approval") is True


def test_escalation_correctness_false_when_expected_but_did_not_escalate() -> None:
    assert check_escalation_correctness(True, "awaiting_approval") is False


def test_escalation_correctness_false_when_escalated_but_not_expected() -> None:
    assert check_escalation_correctness(False, "escalated") is False


# --- check_valid_action_type ---


def test_valid_action_type_none_when_not_reached() -> None:
    assert check_valid_action_type(None) is None


def test_valid_action_type_true_for_a_fixed_value() -> None:
    assert check_valid_action_type(ActionType.RESTART_SERVICE.value) is True


def test_valid_action_type_false_for_an_unknown_value() -> None:
    assert check_valid_action_type("delete_everything") is False


# --- check_evidence_present_at_each_stage ---


def test_evidence_present_true_when_every_reached_stage_has_evidence() -> None:
    assert check_evidence_present_at_each_stage({"triage": 2, "investigation": 4}) is True


def test_evidence_present_false_when_any_reached_stage_has_none() -> None:
    assert check_evidence_present_at_each_stage({"triage": 2, "investigation": 0}) is False


def test_evidence_present_true_when_no_stages_were_reached() -> None:
    assert check_evidence_present_at_each_stage({}) is True


# --- check_validator_not_bypassed ---


def _passing_incident(status: str) -> Incident:
    return Incident(
        trigger="t",
        evidence=["e"],
        status=status,
        proposed_action_type=ActionType.RESTART_SERVICE.value,
        action_justification="justification",
        action_detail="detail",
        action_risk_level="low",
    )


def test_validator_not_bypassed_true_when_not_awaiting_approval() -> None:
    incident = Incident(trigger="t", evidence=[], status="escalated")
    assert check_validator_not_bypassed("escalated", incident) is True


def test_validator_not_bypassed_true_when_awaiting_approval_and_rules_pass() -> None:
    incident = _passing_incident("awaiting_approval")
    assert check_validator_not_bypassed("awaiting_approval", incident) is True


def test_validator_not_bypassed_false_when_awaiting_approval_but_rules_would_fail() -> None:
    # Structurally shouldn't happen (the workflow only reaches AWAITING_APPROVAL
    # via a passing Validator call) -- this proves the audit actually catches it
    # if it ever did.
    incident = _passing_incident("awaiting_approval")
    incident.action_justification = None
    assert check_validator_not_bypassed("awaiting_approval", incident) is False


# --- extract_call_records ---


def _span(
    name: str, model: str, input_tokens: int, output_tokens: int, start: int, end: int
) -> SimpleNamespace:
    return SimpleNamespace(
        name=name,
        attributes={
            "gen_ai.request.model": model,
            "gen_ai.usage.input_tokens": input_tokens,
            "gen_ai.usage.output_tokens": output_tokens,
        },
        start_time=start,
        end_time=end,
    )


def test_extract_call_records_reads_gen_ai_attributes_and_duration() -> None:
    spans = [_span("triage.anthropic_call", "claude-sonnet-5", 100, 50, 0, 2_000_000)]
    records = extract_call_records(spans)
    assert records == [CallRecord("triage", "claude-sonnet-5", 100, 50, 2.0)]


def test_extract_call_records_ignores_non_anthropic_call_spans() -> None:
    spans = [
        SimpleNamespace(name="fastapi.request", attributes={}, start_time=0, end_time=1),
        _span("judge.anthropic_call", "claude-sonnet-5", 10, 5, 0, 1_000_000),
    ]
    records = extract_call_records(spans)
    assert len(records) == 1
    assert records[0].stage == "judge"


# --- cost arithmetic ---

_TRIAGE = CallRecord("triage", "claude-sonnet-5", 1_000_000, 0, 1.0)  # $2.00 at $2/M input
_JUDGE = CallRecord("judge", "claude-sonnet-5", 0, 1_000_000, 1.0)  # $10.00 at $10/M output


def test_cost_for_stage_sums_only_that_stage() -> None:
    assert cost_for_stage([_TRIAGE, _JUDGE], "triage") == Decimal("2.000000")


def test_total_incident_cost_excludes_judge() -> None:
    assert total_incident_cost([_TRIAGE, _JUDGE]) == Decimal("2.000000")


def test_judge_cost_excludes_agent_stages() -> None:
    assert judge_cost([_TRIAGE, _JUDGE]) == Decimal("10.000000")


def test_total_incident_cost_is_zero_with_no_records() -> None:
    assert total_incident_cost([]) == Decimal("0")


def test_latency_ms_by_stage_sums_per_stage() -> None:
    records = [
        CallRecord("triage", "m", 0, 0, 5.0),
        CallRecord("triage", "m", 0, 0, 3.0),
        CallRecord("judge", "m", 0, 0, 7.0),
    ]
    assert latency_ms_by_stage(records) == {"triage": 8.0, "judge": 7.0}


# --- run_rule_based_checks aggregator ---


def test_run_rule_based_checks_aggregates_all_dimensions() -> None:
    incident = _passing_incident("awaiting_approval")
    scenario = Scenario(
        id="s1",
        category="api_failure",
        trigger="t",
        expected=ExpectedOutcome(severity="high", should_escalate=False),
    )
    result = run_rule_based_checks(incident, scenario, [_TRIAGE], {"triage": 1})

    assert result.final_status == "awaiting_approval"
    assert result.escalation_correct is True
    assert result.valid_action_type is True
    assert result.evidence_present_at_each_stage is True
    assert result.validator_not_bypassed is True
    assert result.cost_usd == Decimal("2.000000")
    assert result.judge_cost_usd == Decimal("0")


# --- scenario loading/validation ---


def _write_yaml(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "scenarios.yaml"
    path.write_text(content)
    return path


_ONE_SCENARIO_YAML = """
- id: s1
  category: api_failure
  trigger: "some trigger text"
  expected:
    severity: high
    should_escalate: false
"""


def test_load_scenarios_parses_a_valid_file(tmp_path: Path) -> None:
    path = _write_yaml(tmp_path, _ONE_SCENARIO_YAML)
    scenarios = load_scenarios(path)
    assert len(scenarios) == 1
    assert scenarios[0].id == "s1"
    assert scenarios[0].expected.severity == "high"


def test_load_scenarios_rejects_a_non_list_file(tmp_path: Path) -> None:
    path = _write_yaml(tmp_path, "not_a_list: true")
    with pytest.raises(ScenarioSetValidationError):
        load_scenarios(path)


def _scenario(id_: str, category: str) -> Scenario:
    return Scenario(
        id=id_,
        category=category,
        trigger="t",
        expected=ExpectedOutcome(severity="high", should_escalate=False),
    )


def _full_valid_set() -> list[Scenario]:
    categories = [
        "api_failure",
        "auth_failure",
        "dependency_failure",
        "database_problem",
        "deployment_failure",
        "latency_problem",
    ]
    return [_scenario(f"{cat}_{i}", cat) for cat in categories for i in range(3)]


def test_validate_scenario_set_accepts_18_balanced_scenarios() -> None:
    validate_scenario_set(_full_valid_set())


def test_validate_scenario_set_rejects_wrong_total_count() -> None:
    with pytest.raises(ScenarioSetValidationError):
        validate_scenario_set(_full_valid_set()[:-1])


def test_validate_scenario_set_rejects_duplicate_ids() -> None:
    scenarios = _full_valid_set()
    scenarios[1] = _scenario(scenarios[0].id, scenarios[1].category)
    with pytest.raises(ScenarioSetValidationError):
        validate_scenario_set(scenarios)


def test_validate_scenario_set_rejects_missing_category() -> None:
    scenarios = [s for s in _full_valid_set() if s.category != "latency_problem"]
    scenarios += [_scenario(f"api_failure_extra_{i}", "api_failure") for i in range(3)]
    with pytest.raises(ScenarioSetValidationError):
        validate_scenario_set(scenarios)


def test_validate_scenario_set_rejects_unbalanced_categories() -> None:
    scenarios = _full_valid_set()
    # Move the 4th scenario (first of the 2nd category block) into the 1st
    # category instead -- total stays 18, but now one category has 4 and
    # another has 2.
    scenarios[3] = _scenario(scenarios[3].id, scenarios[0].category)
    with pytest.raises(ScenarioSetValidationError):
        validate_scenario_set(scenarios)
