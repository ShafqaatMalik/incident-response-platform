from app.models.incident import ActionType, RiskLevel
from app.policies.remediation_policy import ACTION_RISK_LEVELS, risk_level_for


def test_action_risk_levels_covers_every_action_type_exactly() -> None:
    assert set(ACTION_RISK_LEVELS.keys()) == set(ActionType)


def test_action_risk_levels_match_the_fixed_user_specified_mapping() -> None:
    assert ACTION_RISK_LEVELS[ActionType.RESTART_SERVICE] == RiskLevel.MEDIUM
    assert ACTION_RISK_LEVELS[ActionType.ROLLBACK_DEPLOYMENT] == RiskLevel.HIGH
    assert ACTION_RISK_LEVELS[ActionType.SCALE_UP] == RiskLevel.LOW
    assert ACTION_RISK_LEVELS[ActionType.DISABLE_TRAFFIC] == RiskLevel.HIGH
    assert ACTION_RISK_LEVELS[ActionType.NO_ACTION_NEEDED] == RiskLevel.LOW
    assert ACTION_RISK_LEVELS[ActionType.MANUAL_INVESTIGATION_REQUIRED] == RiskLevel.NONE


def test_risk_level_for_matches_the_mapping_for_every_action_type() -> None:
    for action_type in ActionType:
        assert risk_level_for(action_type) == ACTION_RISK_LEVELS[action_type]
