import json
import random
import urllib.error
from unittest.mock import MagicMock, patch

from trigger_incident import (
    CATEGORIES,
    STAGES,
    build_inject_request,
    build_stage_request,
    inject,
    main,
    run_pipeline,
    run_stage,
)


def _response(body: dict) -> MagicMock:
    response = MagicMock()
    response.read.return_value = json.dumps(body).encode("utf-8")
    response.__enter__.return_value = response
    return response


def test_build_inject_request_sets_api_key_header_and_json_body() -> None:
    request = build_inject_request("https://example.com", "secret-key", "latency_spike")
    assert request.full_url == "https://example.com/internal/failures/inject"
    assert request.get_header("X-api-key") == "secret-key"
    assert json.loads(request.data) == {"category": "latency_spike"}


def test_build_stage_request_targets_correct_path() -> None:
    request = build_stage_request("https://example.com", "secret-key", "abc-123", "triage")
    assert request.full_url == "https://example.com/internal/incidents/abc-123/triage"
    assert request.get_header("X-api-key") == "secret-key"


def test_inject_picks_one_of_the_three_categories_and_is_varied() -> None:
    rng = random.Random(1)
    seen_categories = set()
    captured_requests = []
    with patch(
        "trigger_incident.urllib.request.urlopen",
        side_effect=lambda request, timeout: (
            captured_requests.append(request) or _response({"id": "abc"})
        ),
    ):
        for _ in range(30):
            inject("https://example.com", "secret-key", rng=rng)

    for request in captured_requests:
        category = json.loads(request.data)["category"]
        assert category in CATEGORIES
        seen_categories.add(category)
    assert len(seen_categories) > 1


def test_inject_returns_incident_id_on_success() -> None:
    with patch(
        "trigger_incident.urllib.request.urlopen", return_value=_response({"id": "abc-123"})
    ):
        assert inject("https://example.com", "secret-key") == "abc-123"


def test_inject_returns_none_on_http_error() -> None:
    error = urllib.error.HTTPError("url", 429, "cap exceeded", {}, None)
    with patch("trigger_incident.urllib.request.urlopen", side_effect=error):
        assert inject("https://example.com", "secret-key") is None


def test_inject_returns_none_on_network_error() -> None:
    with patch(
        "trigger_incident.urllib.request.urlopen",
        side_effect=urllib.error.URLError("connection refused"),
    ):
        assert inject("https://example.com", "secret-key") is None


def test_run_stage_returns_status_on_success() -> None:
    with patch(
        "trigger_incident.urllib.request.urlopen", return_value=_response({"status": "triaged"})
    ):
        ok, status = run_stage("https://example.com", "secret-key", "abc-123", "triage")
    assert ok is True
    assert status == "triaged"


def test_run_stage_returns_false_on_http_error() -> None:
    error = urllib.error.HTTPError("url", 429, "budget exceeded", {}, None)
    with patch("trigger_incident.urllib.request.urlopen", side_effect=error):
        ok, status = run_stage("https://example.com", "secret-key", "abc-123", "triage")
    assert ok is False
    assert status is None


def test_run_pipeline_runs_all_stages_in_order_on_success() -> None:
    responses = [_response({"status": f"stage-{i}"}) for i in range(len(STAGES))]
    with patch("trigger_incident.urllib.request.urlopen", side_effect=responses):
        outcome = run_pipeline("https://example.com", "secret-key", "abc-123")
    assert outcome == "completed -> stage-4"


def test_run_pipeline_stops_early_on_failed_stage() -> None:
    ok_response = _response({"status": "triaged"})
    error = urllib.error.HTTPError("url", 500, "boom", {}, None)
    with patch("trigger_incident.urllib.request.urlopen", side_effect=[ok_response, error]):
        outcome = run_pipeline("https://example.com", "secret-key", "abc-123")
    assert outcome == "stopped at investigate (call failed)"


def test_run_pipeline_stops_on_escalation_without_treating_it_as_a_failure() -> None:
    responses = [
        _response({"status": "triaged"}),
        _response({"status": "escalated"}),
    ]
    with patch("trigger_incident.urllib.request.urlopen", side_effect=responses):
        outcome = run_pipeline("https://example.com", "secret-key", "abc-123")
    assert outcome == "escalated during investigate"


def test_main_exits_1_when_env_vars_missing(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.delenv("TARGET_BASE_URL", raising=False)
    monkeypatch.delenv("API_KEY", raising=False)
    assert main() == 1


def test_main_exits_0_when_injection_fails(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setenv("TARGET_BASE_URL", "https://example.com")
    monkeypatch.setenv("API_KEY", "secret-key")
    with patch("trigger_incident.inject", return_value=None):
        assert main() == 0


def test_main_exits_0_after_a_full_pipeline_run(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setenv("TARGET_BASE_URL", "https://example.com")
    monkeypatch.setenv("API_KEY", "secret-key")
    with (
        patch("trigger_incident.inject", return_value="abc-123"),
        patch("trigger_incident.run_pipeline", return_value="completed -> awaiting_approval"),
    ):
        assert main() == 0
