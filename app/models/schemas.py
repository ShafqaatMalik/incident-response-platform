import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    text: str = Field(min_length=1, max_length=50_000)


class DocumentResponse(BaseModel):
    id: uuid.UUID
    title: str | None
    source_text: str
    summary: str
    word_count: int
    sentence_count: int
    readability_score: float
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    limit: int
    offset: int


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
