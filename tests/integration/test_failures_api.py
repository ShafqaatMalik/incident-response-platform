from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from app.models.schemas import TriageResult

TRIAGE_RESULT = TriageResult(
    severity="high",
    affected_service="checkout-api",
    symptoms=["elevated 500s"],
    initial_evidence=["500s in logs"],
)


@pytest.mark.parametrize(
    "category",
    ["dependency_timeout", "elevated_error_rate", "latency_spike"],
)
async def test_inject_failure_happy_path(
    client: AsyncClient, auth_headers: dict[str, str], category: str
) -> None:
    resp = await client.post(
        "/internal/failures/inject", json={"category": category}, headers=auth_headers
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "detected"
    assert body["trigger"]
    assert body["evidence"]
    assert body["severity"] is None


async def test_inject_failure_requires_auth(client: AsyncClient) -> None:
    resp = await client.post("/internal/failures/inject", json={"category": "latency_spike"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthorized"


async def test_inject_failure_rejects_unknown_category(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/internal/failures/inject", json={"category": "not_a_real_category"}, headers=auth_headers
    )
    assert resp.status_code == 422


async def test_inject_failure_blocked_with_429_once_cap_exceeded(
    client: AsyncClient, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DAILY_FAILURE_INJECTION_LIMIT", "0")
    get_settings.cache_clear()
    try:
        resp = await client.post(
            "/internal/failures/inject",
            json={"category": "dependency_timeout"},
            headers=auth_headers,
        )
    finally:
        get_settings.cache_clear()

    assert resp.status_code == 429
    body = resp.json()
    assert body["error"]["code"] == "injection_cap_exceeded"
    assert "daily failure injection cap" in body["error"]["message"].lower()


async def test_injected_incident_proceeds_through_normal_triage(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    inject_resp = await client.post(
        "/internal/failures/inject",
        json={"category": "dependency_timeout"},
        headers=auth_headers,
    )
    incident_id = inject_resp.json()["id"]

    with patch(
        "app.orchestration.triage_workflow.call_triage_agent_with_retry",
        AsyncMock(return_value=TRIAGE_RESULT),
    ):
        resp = await client.post(f"/internal/incidents/{incident_id}/triage", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json()["status"] == "triaged"
