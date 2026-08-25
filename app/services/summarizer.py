import re
from collections import Counter

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_WORD_RE = re.compile(r"[A-Za-z']+")

_STOPWORDS = frozenset(
    """
    a an the and or but if while of to in on for with as at by from
    is are was were be been being this that these those it its it's
    he she they them his her their i you we me my your our us
    not no do does did have has had will would can could should
    so than then there here what which who whom into out up down
    """.split()  # noqa: SIM905 — a plain readable word list, not worth a giant list literal
)


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text.strip()) if s.strip()]


def _word_frequencies(text: str) -> Counter[str]:
    words = [w.lower() for w in _WORD_RE.findall(text) if len(w) > 1]
    words = [w for w in words if w not in _STOPWORDS]
    return Counter(words)


def _score_sentence(sentence: str, frequencies: Counter[str]) -> float:
    words = [w.lower() for w in _WORD_RE.findall(sentence)]
    if not words:
        return 0.0
    return sum(frequencies.get(w, 0) for w in words) / len(words)


def extractive_summary(text: str, max_sentences: int = 3) -> str:
    """Deterministic frequency-based extractive summary.

    Scores each sentence by the average frequency of its (non-stopword)
    words, then keeps the top-scoring sentences in their original order.
    """
    sentences = _split_sentences(text)
    if not sentences:
        raise ValueError("Text contains no sentences to summarize.")
    if len(sentences) <= max_sentences:
        return " ".join(sentences)

    frequencies = _word_frequencies(text)
    scores = [_score_sentence(s, frequencies) for s in sentences]
    ranked = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)
    top_indices = {i for i, _ in ranked[:max_sentences]}
    return " ".join(s for i, s in enumerate(sentences) if i in top_indices)
