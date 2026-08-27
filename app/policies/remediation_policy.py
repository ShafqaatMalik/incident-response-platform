from app.models.incident import ActionType, RiskLevel

ACTION_RISK_LEVELS: dict[ActionType, RiskLevel] = {
    ActionType.RESTART_SERVICE: RiskLevel.MEDIUM,
    ActionType.ROLLBACK_DEPLOYMENT: RiskLevel.HIGH,
    ActionType.SCALE_UP: RiskLevel.LOW,
    ActionType.DISABLE_TRAFFIC: RiskLevel.HIGH,
    ActionType.NO_ACTION_NEEDED: RiskLevel.LOW,
    ActionType.MANUAL_INVESTIGATION_REQUIRED: RiskLevel.NONE,
}


def risk_level_for(action_type: ActionType) -> RiskLevel:
    return ACTION_RISK_LEVELS[action_type]
