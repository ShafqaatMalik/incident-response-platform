from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from app.models.schemas import DiagnosisResult, InvestigationResult, TriageResult

TRIAGE_RESULT = TriageResult(
    severity="high",
    affected_service="checkout-api",
    symptoms=["elevated 500s"],
    initial_evidence=["500s in logs"],
)

INVESTIGATION_RESULT = InvestigationResult(
    error_patterns=["connection pool exhausted"],
    deployment_correlation="deployed 8 min before onset",
    service_health_summary="elevated error rate and latency",
    confidence="high",
    evidence=["deploy v1.42.0 at 14:32 UTC"],
)

DIAGNOSIS_RESULT = DiagnosisResult(
    root_cause="database connection pool exhaustion from a recent deploy",
    evidence=["connection pool at 0 available connections"],
    confidence="high",
    alternative_explanations=["no plausible alternative explanations found"],
)


async def test_create_incident(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    resp = await client.post(
        "/internal/incidents",
        json={"trigger": "Checkout API returning 500s", "initial_evidence": ["500s in logs"]},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "detected"
    assert body["trigger"] == "Checkout API returning 500s"
    assert body["evidence"] == ["500s in logs"]
    assert body["severity"] is None


async def test_create_incident_requires_auth(client: AsyncClient) -> None:
    resp = await client.post("/internal/incidents", json={"trigger": "Something broke"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthorized"


async def test_create_incident_rejects_empty_trigger(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.post("/internal/incidents", json={"trigger": ""}, headers=auth_headers)
    assert resp.status_code == 422


async def test_triage_missing_incident_returns_404(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/internal/incidents/00000000-0000-0000-0000-000000000000/triage",
        headers=auth_headers,
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


async def test_triage_happy_path_transitions_to_triaged(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    create_resp = await client.post(
        "/internal/incidents",
        json={"trigger": "Checkout API returning 500s", "initial_evidence": ["500s in logs"]},
        headers=auth_headers,
    )
    incident_id = create_resp.json()["id"]

    with patch(
        "app.orchestration.triage_workflow.call_triage_agent_with_retry",
        AsyncMock(return_value=TRIAGE_RESULT),
    ):
        resp = await client.post(f"/internal/incidents/{incident_id}/triage", headers=auth_headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "triaged"
    assert body["severity"] == "high"
    assert body["affected_service"] == "checkout-api"
    assert "500s in logs" in body["evidence"]


async def test_triage_twice_returns_409(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    create_resp = await client.post(
        "/internal/incidents",
        json={"trigger": "Checkout API returning 500s"},
        headers=auth_headers,
    )
    incident_id = create_resp.json()["id"]

    with patch(
        "app.orchestration.triage_workflow.call_triage_agent_with_retry",
        AsyncMock(return_value=TRIAGE_RESULT),
    ):
        first = await client.post(f"/internal/incidents/{incident_id}/triage", headers=auth_headers)
        assert first.status_code == 200

        second = await client.post(
            f"/internal/incidents/{incident_id}/triage", headers=auth_headers
        )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "invalid_transition"


async def test_investigate_missing_incident_returns_404(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/internal/incidents/00000000-0000-0000-0000-000000000000/investigate",
        headers=auth_headers,
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


async def test_investigate_happy_path_transitions_to_investigating(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    create_resp = await client.post(
        "/internal/incidents",
        json={"trigger": "Checkout API returning 500s", "initial_evidence": ["500s in logs"]},
        headers=auth_headers,
    )
    incident_id = create_resp.json()["id"]

    with patch(
        "app.orchestration.triage_workflow.call_triage_agent_with_retry",
        AsyncMock(return_value=TRIAGE_RESULT),
    ):
        triage_resp = await client.post(
            f"/internal/incidents/{incident_id}/triage", headers=auth_headers
        )
    assert triage_resp.status_code == 200

    with patch(
        "app.orchestration.investigation_workflow.call_investigation_agent_with_retry",
        AsyncMock(return_value=INVESTIGATION_RESULT),
    ):
        resp = await client.post(
            f"/internal/incidents/{incident_id}/investigate", headers=auth_headers
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "investigating"
    assert body["error_patterns"] == ["connection pool exhausted"]
    assert body["deployment_correlation"] == "deployed 8 min before onset"
    assert body["service_health_summary"] == "elevated error rate and latency"
    assert body["investigation_confidence"] == "high"
    assert "500s in logs" in body["evidence"]
    assert "deploy v1.42.0 at 14:32 UTC" in body["evidence"]


async def test_investigate_twice_returns_409(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    create_resp = await client.post(
        "/internal/incidents",
        json={"trigger": "Checkout API returning 500s"},
        headers=auth_headers,
    )
    incident_id = create_resp.json()["id"]

    with patch(
        "app.orchestration.triage_workflow.call_triage_agent_with_retry",
        AsyncMock(return_value=TRIAGE_RESULT),
    ):
        await client.post(f"/internal/incidents/{incident_id}/triage", headers=auth_headers)

    with patch(
        "app.orchestration.investigation_workflow.call_investigation_agent_with_retry",
        AsyncMock(return_value=INVESTIGATION_RESULT),
    ):
        first = await client.post(
            f"/internal/incidents/{incident_id}/investigate", headers=auth_headers
        )
        assert first.status_code == 200

        second = await client.post(
            f"/internal/incidents/{incident_id}/investigate", headers=auth_headers
        )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "invalid_transition"


async def test_investigate_before_triage_returns_409_not_500(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    create_resp = await client.post(
        "/internal/incidents",
        json={"trigger": "Checkout API returning 500s"},
        headers=auth_headers,
    )
    incident_id = create_resp.json()["id"]

    with patch(
        "app.orchestration.investigation_workflow.call_investigation_agent_with_retry",
        AsyncMock(),
    ) as mock:
        resp = await client.post(
            f"/internal/incidents/{incident_id}/investigate", headers=auth_headers
        )

    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "invalid_transition"
    mock.assert_not_called()


async def test_diagnose_missing_incident_returns_404(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/internal/incidents/00000000-0000-0000-0000-000000000000/diagnose",
        headers=auth_headers,
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


async def test_diagnose_happy_path_transitions_to_diagnosed(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    create_resp = await client.post(
        "/internal/incidents",
        json={"trigger": "Checkout API returning 500s", "initial_evidence": ["500s in logs"]},
        headers=auth_headers,
    )
    incident_id = create_resp.json()["id"]

    with patch(
        "app.orchestration.triage_workflow.call_triage_agent_with_retry",
        AsyncMock(return_value=TRIAGE_RESULT),
    ):
        await client.post(f"/internal/incidents/{incident_id}/triage", headers=auth_headers)

    with patch(
        "app.orchestration.investigation_workflow.call_investigation_agent_with_retry",
        AsyncMock(return_value=INVESTIGATION_RESULT),
    ):
        await client.post(f"/internal/incidents/{incident_id}/investigate", headers=auth_headers)

    with patch(
        "app.orchestration.diagnosis_workflow.call_diagnosis_agent_with_retry",
        AsyncMock(return_value=DIAGNOSIS_RESULT),
    ):
        resp = await client.post(
            f"/internal/incidents/{incident_id}/diagnose", headers=auth_headers
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "diagnosed"
    assert body["root_cause"] == "database connection pool exhaustion from a recent deploy"
    assert body["alternative_explanations"] == ["no plausible alternative explanations found"]
    assert body["diagnosis_confidence"] == "high"
    assert "500s in logs" in body["evidence"]
    assert "deploy v1.42.0 at 14:32 UTC" in body["evidence"]
    assert "connection pool at 0 available connections" in body["evidence"]


async def test_diagnose_twice_returns_409(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    create_resp = await client.post(
        "/internal/incidents",
        json={"trigger": "Checkout API returning 500s"},
        headers=auth_headers,
    )
    incident_id = create_resp.json()["id"]

    with patch(
        "app.orchestration.triage_workflow.call_triage_agent_with_retry",
        AsyncMock(return_value=TRIAGE_RESULT),
    ):
        await client.post(f"/internal/incidents/{incident_id}/triage", headers=auth_headers)

    with patch(
        "app.orchestration.investigation_workflow.call_investigation_agent_with_retry",
        AsyncMock(return_value=INVESTIGATION_RESULT),
    ):
        await client.post(f"/internal/incidents/{incident_id}/investigate", headers=auth_headers)

    with patch(
        "app.orchestration.diagnosis_workflow.call_diagnosis_agent_with_retry",
        AsyncMock(return_value=DIAGNOSIS_RESULT),
    ):
        first = await client.post(
            f"/internal/incidents/{incident_id}/diagnose", headers=auth_headers
        )
        assert first.status_code == 200

        second = await client.post(
            f"/internal/incidents/{incident_id}/diagnose", headers=auth_headers
        )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "invalid_transition"


async def test_diagnose_before_investigate_returns_409_not_500(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    create_resp = await client.post(
        "/internal/incidents",
        json={"trigger": "Checkout API returning 500s"},
        headers=auth_headers,
    )
    incident_id = create_resp.json()["id"]

    with patch(
        "app.orchestration.triage_workflow.call_triage_agent_with_retry",
        AsyncMock(return_value=TRIAGE_RESULT),
    ):
        await client.post(f"/internal/incidents/{incident_id}/triage", headers=auth_headers)

    with patch(
        "app.orchestration.diagnosis_workflow.call_diagnosis_agent_with_retry",
        AsyncMock(),
    ) as mock:
        resp = await client.post(
            f"/internal/incidents/{incident_id}/diagnose", headers=auth_headers
        )

    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "invalid_transition"
    mock.assert_not_called()
