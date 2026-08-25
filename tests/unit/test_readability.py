from app.services.readability import compute_readability


def test_computes_positive_metrics_for_normal_text() -> None:
    text = "The cat sat on the mat. It was a sunny day outside."
    metrics = compute_readability(text)
    assert metrics.word_count > 0
    assert metrics.sentence_count >= 1
    assert isinstance(metrics.readability_score, float)


def test_simple_text_scores_higher_than_complex_text() -> None:
    simple = "The cat sat on the mat. The dog ran fast."
    complex_text = (
        "The multifaceted epistemological ramifications of interdisciplinary "
        "phenomenological inquiry necessitate an exceptionally sophisticated "
        "hermeneutic methodology."
    )
    simple_score = compute_readability(simple).readability_score
    complex_score = compute_readability(complex_text).readability_score
    assert simple_score > complex_score
