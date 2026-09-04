from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session, require_api_key
from app.core.config import Settings, get_settings
from app.core.rate_limit import limiter, rate_limit_value
from app.models.incident import Incident, IncidentStatus
from app.models.schemas import FailureInjectionRequest, IncidentResponse
from app.policies.failure_injection_policy import (
    InjectionCapExceededError,
    build_injection_trigger,
    is_injection_cap_exceeded,
    record_injection,
)

router = APIRouter(
    prefix="/internal/failures", tags=["failures"], dependencies=[Depends(require_api_key)]
)


@router.post("/inject", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(rate_limit_value)
async def inject_failure(
    request: Request,
    response: Response,
    payload: FailureInjectionRequest,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> Incident:
    if await is_injection_cap_exceeded(session, settings.daily_failure_injection_limit):
        raise InjectionCapExceededError(
            f"Daily failure injection cap of {settings.daily_failure_injection_limit} reached."
        )

    trigger, evidence = build_injection_trigger(payload.category)
    incident = Incident(trigger=trigger, evidence=evidence, status=IncidentStatus.DETECTED.value)
    session.add(incident)
    await record_injection(session)
    await session.commit()
    await session.refresh(incident)
    return incident
