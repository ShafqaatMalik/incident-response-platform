from dataclasses import dataclass

import textstat


@dataclass(frozen=True)
class ReadabilityMetrics:
    word_count: int
    sentence_count: int
    readability_score: float


def compute_readability(text: str) -> ReadabilityMetrics:
    return ReadabilityMetrics(
        word_count=textstat.lexicon_count(text, removepunct=True),
        sentence_count=textstat.sentence_count(text),
        readability_score=textstat.flesch_reading_ease(text),
    )
