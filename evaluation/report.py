import json
from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from harness import ScenarioResult

REPORTS_DIR = Path(__file__).parent / "reports"


def _json_default(obj: object) -> float:
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Not JSON serializable: {obj!r}")


def scenario_result_to_dict(result: ScenarioResult) -> dict:
    return {
        "scenario_id": result.scenario.id,
        "category": result.scenario.category,
        "trigger": result.scenario.trigger,
        "expected": result.scenario.expected.model_dump(),
        "incident_id": result.incident_id,
        "harness_error": result.harness_error,
        "rule_based": asdict(result.rule_based) if result.rule_based else None,
        "judge": result.judge.model_dump() if result.judge else None,
        "judge_error": result.judge_error,
    }


def _rate(
    results: list[ScenarioResult], pred: Callable[[ScenarioResult], bool | None]
) -> float | None:
    values = [pred(r) for r in results]
    values = [v for v in values if v is not None]
    if not values:
        return None
    return sum(1 for v in values if v) / len(values)


def build_aggregate(results: list[ScenarioResult]) -> dict:
    completed = [r for r in results if r.harness_error is None]

    total_incident_cost = sum(
        (r.rule_based.cost_usd for r in completed if r.rule_based), Decimal("0")
    )
    total_judge_cost = sum(
        (r.rule_based.judge_cost_usd for r in completed if r.rule_based), Decimal("0")
    )

    judge_verdict_counts: dict[str, dict[str, int]] = {}
    for dimension in ("severity_verdict", "diagnosis_verdict", "remediation_verdict"):
        counts: dict[str, int] = {}
        for r in completed:
            if r.judge is None:
                continue
            value = getattr(r.judge, dimension)
            counts[value] = counts.get(value, 0) + 1
        judge_verdict_counts[dimension] = counts

    return {
        "total_scenarios": len(results),
        "harness_aborted": len(results) - len(completed),
        "completed": len(completed),
        "escalation_correctness_rate": _rate(
            completed, lambda r: r.rule_based.escalation_correct if r.rule_based else None
        ),
        "valid_action_type_rate": _rate(
            completed, lambda r: r.rule_based.valid_action_type if r.rule_based else None
        ),
        "evidence_present_rate": _rate(
            completed,
            lambda r: r.rule_based.evidence_present_at_each_stage if r.rule_based else None,
        ),
        "validator_not_bypassed_rate": _rate(
            completed, lambda r: r.rule_based.validator_not_bypassed if r.rule_based else None
        ),
        "judge_failures": sum(1 for r in completed if r.judge_error),
        "hallucination_detected_count": sum(
            1 for r in completed if r.judge and r.judge.hallucination_detected
        ),
        "judge_verdict_counts": judge_verdict_counts,
        "total_incident_cost_usd": float(total_incident_cost),
        "total_judge_cost_usd": float(total_judge_cost),
        "mean_incident_cost_usd": (
            float(total_incident_cost / len(completed)) if completed else None
        ),
    }


def render_markdown(results: list[ScenarioResult], aggregate: dict) -> str:
    lines = ["# Evaluation Report", ""]
    lines.append(f"Generated: {datetime.now(UTC).isoformat()}")
    lines.append("")
    lines.append("## Aggregate")
    lines.append("")
    for key, value in aggregate.items():
        if key == "judge_verdict_counts":
            continue
        lines.append(f"- **{key}**: {value}")
    lines.append("")
    lines.append("### Judge verdict distribution")
    for dimension, counts in aggregate["judge_verdict_counts"].items():
        lines.append(f"- **{dimension}**: {counts}")
    lines.append("")
    lines.append("## Per-scenario detail")
    lines.append("")

    for r in results:
        lines.append(f"### {r.scenario.id} ({r.scenario.category})")
        lines.append("")
        lines.append(f"Trigger: {r.scenario.trigger}")
        lines.append("")
        if r.harness_error:
            lines.append(f"**Harness aborted:** {r.harness_error}")
            lines.append("")
            continue

        lines.append(
            f"Expected: severity={r.scenario.expected.severity.value}, "
            f"root_cause={r.scenario.expected.root_cause!r}, "
            f"proposed_action={r.scenario.expected.proposed_action!r}, "
            f"should_escalate={r.scenario.expected.should_escalate}"
        )
        lines.append("")
        status = r.rule_based.final_status if r.rule_based else "n/a"
        lines.append(f"Actual final status: `{status}`")
        lines.append("")
        if r.rule_based:
            lines.append(
                f"Rule-based: escalation_correct={r.rule_based.escalation_correct}, "
                f"valid_action_type={r.rule_based.valid_action_type}, "
                f"evidence_present_at_each_stage={r.rule_based.evidence_present_at_each_stage}, "
                f"validator_not_bypassed={r.rule_based.validator_not_bypassed}, "
                f"cost_usd={r.rule_based.cost_usd}, judge_cost_usd={r.rule_based.judge_cost_usd}"
            )
            lines.append("")

        if r.judge_error:
            lines.append(f"**Judge failed:** {r.judge_error}")
        elif r.judge:
            j = r.judge
            lines.append(f"- **severity_verdict**: {j.severity_verdict} — {j.severity_reasoning}")
            lines.append(
                f"- **diagnosis_verdict**: {j.diagnosis_verdict} — {j.diagnosis_reasoning}"
            )
            lines.append(
                f"- **remediation_verdict**: {j.remediation_verdict} — {j.remediation_reasoning}"
            )
            lines.append(
                f"- **hallucination_detected**: {j.hallucination_detected} — "
                f"{j.hallucination_reasoning}"
            )
            if j.unsupported_claims:
                lines.append(f"  - unsupported claims: {j.unsupported_claims}")
        lines.append("")

    return "\n".join(lines)


def write_report(results: list[ScenarioResult], out_dir: Path = REPORTS_DIR) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")

    aggregate = build_aggregate(results)
    json_payload = {
        "aggregate": aggregate,
        "scenarios": [scenario_result_to_dict(r) for r in results],
    }

    json_path = out_dir / f"{timestamp}.json"
    json_path.write_text(json.dumps(json_payload, indent=2, default=_json_default))

    md_path = out_dir / f"{timestamp}.md"
    md_path.write_text(render_markdown(results, aggregate))

    return json_path, md_path
