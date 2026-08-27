from dataclasses import dataclass

from app.models.incident import ActionType, Confidence, Incident


@dataclass(frozen=True)
class ValidationResult:
    passed: bool
    reason: str | None = None


def validate_remediation(incident: Incident) -> ValidationResult:
    """Fixed 6-rule check over a remediation proposal already stored on the
    incident. Pure code, no LLM call — see ARCHITECTURE.md §4's Validator
    description."""
    if incident.proposed_action_type not in {a.value for a in ActionType}:
        return ValidationResult(
            passed=False,
            reason=(
                f"Rule 1 failed: '{incident.proposed_action_type}' is not one of the "
                "fixed action types."
            ),
        )
    action_type = ActionType(incident.proposed_action_type)

    if (
        not incident.action_justification
        or not incident.action_detail
        or not incident.action_risk_level
    ):
        return ValidationResult(
            passed=False,
            reason=(
                "Rule 2 failed: action_justification, action_detail, and "
                "action_risk_level must all be non-empty."
            ),
        )

    if action_type == ActionType.ROLLBACK_DEPLOYMENT and not incident.deployment_correlation:
        return ValidationResult(
            passed=False,
            reason=(
                "Rule 3 failed: rollback_deployment requires a non-empty deployment_correlation."
            ),
        )

    if (
        action_type in (ActionType.RESTART_SERVICE, ActionType.DISABLE_TRAFFIC)
        and not incident.evidence
    ):
        return ValidationResult(
            passed=False,
            reason=f"Rule 4 failed: {action_type.value} requires a non-empty evidence list.",
        )

    if action_type == ActionType.SCALE_UP and not incident.service_health_summary:
        return ValidationResult(
            passed=False,
            reason="Rule 5 failed: scale_up requires a non-empty service_health_summary.",
        )

    if (
        action_type == ActionType.NO_ACTION_NEEDED
        and incident.diagnosis_confidence == Confidence.LOW.value
    ):
        return ValidationResult(
            passed=False,
            reason=(
                "Rule 6 failed: no_action_needed is not allowed when diagnosis_confidence is low."
            ),
        )

    return ValidationResult(passed=True)
