import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session, require_api_key
from app.core.config import Settings, get_settings
from app.core.rate_limit import limiter, rate_limit_value
from app.models.incident import Incident, IncidentStatus
from app.models.schemas import (
    ApprovalRequest,
    IncidentCreate,
    IncidentListResponse,
    IncidentResponse,
    RejectionRequest,
)
from app.orchestration.approval_workflow import run_approval, run_rejection
from app.orchestration.diagnosis_workflow import run_diagnosis
from app.orchestration.investigation_workflow import run_investigation
from app.orchestration.remediation_workflow import run_remediation
from app.orchestration.triage_workflow import run_triage
from app.orchestration.validation_workflow import run_validation

router = APIRouter(
    prefix="/internal/incidents", tags=["incidents"], dependencies=[Depends(require_api_key)]
)


@router.get("", response_model=IncidentListResponse)
@limiter.limit(rate_limit_value)
async def list_incidents(
    request: Request,
    response: Response,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> IncidentListResponse:
    total = await session.scalar(select(func.count()).select_from(Incident))
    open_count = await session.scalar(
        select(func.count())
        .select_from(Incident)
        .where(Incident.status.notin_(["approved", "rejected", "escalated"]))
    )
    awaiting_approval_count = await session.scalar(
        select(func.count())
        .select_from(Incident)
        .where(Incident.status == IncidentStatus.AWAITING_APPROVAL.value)
    )
    result = await session.scalars(
        select(Incident).order_by(Incident.created_at.desc()).limit(limit).offset(offset)
    )
    items = list(result.all())
    return IncidentListResponse(
        items=[IncidentResponse.model_validate(i) for i in items],
        total=total or 0,
        limit=limit,
        offset=offset,
        open_count=open_count or 0,
        awaiting_approval_count=awaiting_approval_count or 0,
    )


@router.get("/{incident_id}", response_model=IncidentResponse)
@limiter.limit(rate_limit_value)
async def get_incident(
    request: Request,
    response: Response,
    incident_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> Incident:
    incident = await session.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found.",
        )
    return incident


@router.post("", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(rate_limit_value)
async def create_incident(
    request: Request,
    response: Response,
    payload: IncidentCreate,
    session: AsyncSession = Depends(get_db_session),
) -> Incident:
    incident = Incident(
        trigger=payload.trigger,
        evidence=payload.initial_evidence,
        status=IncidentStatus.DETECTED.value,
    )
    session.add(incident)
    await session.commit()
    await session.refresh(incident)
    return incident


@router.post("/{incident_id}/triage", response_model=IncidentResponse)
@limiter.limit(rate_limit_value)
async def triage_incident(
    request: Request,
    response: Response,
    incident_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> Incident:
    incident = await session.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found.",
        )
    return await run_triage(incident, session, settings)


@router.post("/{incident_id}/investigate", response_model=IncidentResponse)
@limiter.limit(rate_limit_value)
async def investigate_incident(
    request: Request,
    response: Response,
    incident_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> Incident:
    incident = await session.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found.",
        )
    return await run_investigation(incident, session, settings)


@router.post("/{incident_id}/diagnose", response_model=IncidentResponse)
@limiter.limit(rate_limit_value)
async def diagnose_incident(
    request: Request,
    response: Response,
    incident_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> Incident:
    incident = await session.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found.",
        )
    return await run_diagnosis(incident, session, settings)


@router.post("/{incident_id}/remediate", response_model=IncidentResponse)
@limiter.limit(rate_limit_value)
async def remediate_incident(
    request: Request,
    response: Response,
    incident_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> Incident:
    incident = await session.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found.",
        )
    return await run_remediation(incident, session, settings)


@router.post("/{incident_id}/validate", response_model=IncidentResponse)
@limiter.limit(rate_limit_value)
async def validate_incident(
    request: Request,
    response: Response,
    incident_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> Incident:
    incident = await session.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found.",
        )
    return await run_validation(incident, session)


@router.post("/{incident_id}/approve", response_model=IncidentResponse)
@limiter.limit(rate_limit_value)
async def approve_incident(
    request: Request,
    response: Response,
    incident_id: uuid.UUID,
    payload: ApprovalRequest,
    session: AsyncSession = Depends(get_db_session),
) -> Incident:
    incident = await session.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found.",
        )
    return await run_approval(incident, payload.approved_by, session)


@router.post("/{incident_id}/reject", response_model=IncidentResponse)
@limiter.limit(rate_limit_value)
async def reject_incident(
    request: Request,
    response: Response,
    incident_id: uuid.UUID,
    payload: RejectionRequest,
    session: AsyncSession = Depends(get_db_session),
) -> Incident:
    incident = await session.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found.",
        )
    return await run_rejection(incident, payload.rejected_by, payload.rejection_reason, session)
