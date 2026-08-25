import pytest

from app.services.summarizer import _split_sentences, extractive_summary


def test_returns_all_sentences_when_within_limit() -> None:
    text = "One. Two. Three."
    assert extractive_summary(text, max_sentences=5) == "One. Two. Three."


def test_returns_at_most_max_sentences() -> None:
    text = " ".join(
        f"Sentence number {i} contains different unique words each time." for i in range(10)
    )
    summary = extractive_summary(text, max_sentences=3)
    assert len(_split_sentences(summary)) == 3


def test_raises_on_text_with_no_sentences() -> None:
    with pytest.raises(ValueError):
        extractive_summary("   ")


def test_preserves_original_sentence_order() -> None:
    text = "Alpha alpha alpha. Beta. Gamma gamma gamma gamma."
    summary = extractive_summary(text, max_sentences=2)
    assert summary.index("Alpha") < summary.index("Gamma")
