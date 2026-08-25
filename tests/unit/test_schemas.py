import pytest
from pydantic import ValidationError

from app.models.schemas import DocumentCreate


def test_text_is_required() -> None:
    with pytest.raises(ValidationError):
        DocumentCreate()  # type: ignore[call-arg]


def test_rejects_empty_text() -> None:
    with pytest.raises(ValidationError):
        DocumentCreate(text="")


def test_rejects_overlong_text() -> None:
    with pytest.raises(ValidationError):
        DocumentCreate(text="a" * 50_001)


def test_accepts_valid_payload() -> None:
    doc = DocumentCreate(title="Hi", text="Hello world.")
    assert doc.title == "Hi"
    assert doc.text == "Hello world."
