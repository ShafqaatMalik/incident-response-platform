from dataclasses import dataclass

from checks import RuleBasedResult, extract_call_records, run_rule_based_checks
from judge import JUDGE_MODEL, JudgeVerdict, call_judge_with_retry
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from scenarios import Scenario
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.incident import Incident, IncidentStatus
from app.orchestration.diagnosis_workflow import run_diagnosis
from app.orchestration.investigation_workflow import run_investigation
from app.orchestration.remediation_workflow import run_remediation
from app.orchestration.triage_workflow import run_triage
from app.orchestration.validation_workflow import run_validation
from app.policies.budget_policy import BudgetExceededError


@dataclass
class ScenarioResult:
    scenario: Scenario
    incident_id: str | None
    rule_based: RuleBasedResult | None
    judge: JudgeVerdict | None
    judge_error: str | None
    harness_error: str | None = None

    @classmethod
    def harness_aborted(cls, scenario: Scenario, error: str) -> "ScenarioResult":
        return cls(
            scenario=scenario,
            incident_id=None,
            rule_based=None,
            judge=None,
            judge_error=None,
            harness_error=error,
        )


async def run_scenario(
    scenario: Scenario,
    session: AsyncSession,
    settings: Settings,
    exporter: InMemorySpanExporter,
) -> ScenarioResult:
    exporter.clear()
    incident = Incident(
        trigger=scenario.trigger,
        evidence=list(scenario.initial_evidence),
        status=IncidentStatus.DETECTED.value,
    )
    session.add(incident)
    await session.commit()
    await session.refresh(incident)

    stage_evidence_counts: dict[str, int] = {}
    try:
        incident = await run_triage(incident, session, settings)
        stage_evidence_counts["triage"] = len(incident.evidence or [])
        if incident.status == IncidentStatus.TRIAGED.value:
            incident = await run_investigation(incident, session, settings)
            stage_evidence_counts["investigation"] = len(incident.evidence or [])
            if incident.status == IncidentStatus.INVESTIGATING.value:
                incident = await run_diagnosis(incident, session, settings)
                stage_evidence_counts["diagnosis"] = len(incident.evidence or [])
                if incident.status == IncidentStatus.DIAGNOSED.value:
                    incident = await run_remediation(incident, session, settings)
                    if incident.status == IncidentStatus.VALIDATING.value:
                        incident = await run_validation(incident, session)
    except BudgetExceededError as exc:
        return ScenarioResult.harness_aborted(scenario, str(exc))

    records = extract_call_records(exporter.get_finished_spans())
    rule_based = run_rule_based_checks(incident, scenario, records, stage_evidence_counts)
    verdict, judge_error = await call_judge_with_retry(scenario, incident, JUDGE_MODEL)

    return ScenarioResult(
        scenario=scenario,
        incident_id=str(incident.id),
        rule_based=rule_based,
        judge=verdict,
        judge_error=judge_error,
    )
