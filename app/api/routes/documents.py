import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session, require_api_key
from app.core.rate_limit import limiter, rate_limit_value
from app.models.document import Document
from app.models.schemas import DocumentCreate, DocumentListResponse, DocumentResponse
from app.services.readability import compute_readability
from app.services.summarizer import extractive_summary

router = APIRouter(prefix="/documents", tags=["documents"], dependencies=[Depends(require_api_key)])


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(rate_limit_value)
async def create_document(
    request: Request,
    response: Response,
    payload: DocumentCreate,
    session: AsyncSession = Depends(get_db_session),
) -> Document:
    try:
        summary = extractive_summary(payload.text)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Text must contain at least one sentence.",
        ) from exc

    metrics = compute_readability(payload.text)

    document = Document(
        title=payload.title,
        source_text=payload.text,
        summary=summary,
        word_count=metrics.word_count,
        sentence_count=metrics.sentence_count,
        readability_score=metrics.readability_score,
    )
    session.add(document)
    await session.commit()
    await session.refresh(document)
    return document


@router.get("", response_model=DocumentListResponse)
@limiter.limit(rate_limit_value)
async def list_documents(
    request: Request,
    response: Response,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> DocumentListResponse:
    total = await session.scalar(select(func.count()).select_from(Document))
    result = await session.scalars(
        select(Document).order_by(Document.created_at.desc()).limit(limit).offset(offset)
    )
    items = list(result.all())
    return DocumentListResponse(
        items=[DocumentResponse.model_validate(item) for item in items],
        total=total or 0,
        limit=limit,
        offset=offset,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
@limiter.limit(rate_limit_value)
async def get_document(
    request: Request,
    response: Response,
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> Document:
    document = await session.get(Document, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found.",
        )
    return document
