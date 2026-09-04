import json
import random
import urllib.error
from unittest.mock import MagicMock, patch

from send_traffic import SAMPLE_TEXTS, build_request, pick_sample, send_once


def test_pick_sample_returns_one_of_the_fixed_samples() -> None:
    assert pick_sample(random.Random(0)) in SAMPLE_TEXTS


def test_pick_sample_is_varied_across_many_calls() -> None:
    rng = random.Random(1)
    picks = {pick_sample(rng)[0] for _ in range(50)}
    assert len(picks) > 1


def test_build_request_sets_api_key_header_and_json_body() -> None:
    request = build_request("https://example.com", "secret-key", "Title", "Some text.")
    assert request.full_url == "https://example.com/documents"
    assert request.get_header("X-api-key") == "secret-key"
    assert json.loads(request.data) == {"title": "Title", "text": "Some text."}


def test_send_once_returns_true_on_success() -> None:
    response = MagicMock()
    response.status = 201
    response.__enter__.return_value = response
    with patch("send_traffic.urllib.request.urlopen", return_value=response):
        assert send_once("https://example.com", "secret-key") is True


def test_send_once_returns_false_and_does_not_raise_on_failure() -> None:
    with patch(
        "send_traffic.urllib.request.urlopen",
        side_effect=urllib.error.URLError("connection refused"),
    ):
        assert send_once("https://example.com", "secret-key") is False
