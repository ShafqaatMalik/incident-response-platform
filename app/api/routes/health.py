from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session

router = APIRouter(tags=["health"])


@router.get("/health")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(session: AsyncSession = Depends(get_db_session)) -> dict[str, str]:
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not reachable.",
        ) from exc
    return {"status": "ok"}
