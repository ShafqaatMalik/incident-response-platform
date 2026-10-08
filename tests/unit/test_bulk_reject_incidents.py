import importlib.util
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "bulk_reject_incidents.py"


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("bulk_reject_incidents", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bulk = _load_script()

_NOW = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)


def _incident(status: str, hours_ago: int) -> dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "status": status,
        "severity": "low",
        "created_at": (_NOW - timedelta(hours=hours_ago)).isoformat(),
        "trigger": f"trigger {hours_ago}h ago",
    }


class FakeClient:
    """Serves the list endpoint in pages, records every call."""

    def __init__(self, incidents: list[dict[str, Any]], fail_on_post: int | None = None) -> None:
        self.incidents = sorted(incidents, key=lambda i: i["created_at"], reverse=True)
        self.gets: list[str] = []
        self.posts: list[tuple[str, dict[str, Any]]] = []
        self._fail_on_post = fail_on_post

    def get_json(self, path: str) -> dict[str, Any]:
        self.gets.append(path)
        query = dict(p.split("=") for p in path.split("?")[1].split("&"))
        limit, offset = int(query["limit"]), int(query["offset"])
        return {
            "items": self.incidents[offset : offset + limit],
            "total": len(self.incidents),
            "limit": limit,
            "offset": offset,
        }

    def post_json(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        if self._fail_on_post is not None and len(self.posts) == self._fail_on_post:
            raise OSError("boom")
        self.posts.append((path, body))
        return {"status": "rejected"}


def _mixed_incidents() -> list[dict[str, Any]]:
    # 150 awaiting_approval (forces 2 pages) + one of every other status.
    awaiting = [_incident("awaiting_approval", h) for h in range(1, 151)]
    others = [
        _incident(s, 200 + n)
        for n, s in enumerate(
            ["detected", "triaged", "validating", "approved", "rejected", "escalated"]
        )
    ]
    return awaiting + others


def _run(client: FakeClient, **kwargs: Any) -> tuple[int, list[str]]:
    lines: list[str] = []
    params: dict[str, Any] = {"keep_latest": 3, "before": None, "yes": False, "delay": 0.0}
    params.update(kwargs)
    code = bulk.run(client, sleep=lambda _: None, out=lines.append, **params)
    return code, lines


def test_dry_run_makes_no_reject_calls_and_reports_total_seen() -> None:
    client = FakeClient(_mixed_incidents())
    code, lines = _run(client)
    assert code == 0
    assert client.posts == []
    assert len(client.gets) == 2  # paginated: 156 incidents at 100/page
    assert "Incidents seen: 156 (server-reported total: 156)" in lines
    assert "DRY RUN -- would reject: 147" in lines


def test_yes_rejects_only_awaiting_approval_and_never_approves() -> None:
    incidents = _mixed_incidents()
    client = FakeClient(incidents)
    code, _ = _run(client, yes=True)
    assert code == 0

    awaiting_ids = {i["id"] for i in incidents if i["status"] == "awaiting_approval"}
    posted_ids = {path.split("/")[3] for path, _ in client.posts}
    assert len(client.posts) == 147
    assert posted_ids <= awaiting_ids  # non-awaiting_approval statuses are skipped
    assert all(path.endswith("/reject") for path, _ in client.posts)
    assert not any("approve" in path for path, _ in client.posts)
    assert all(
        body == {"rejected_by": "bulk-cleanup", "rejection_reason": bulk.REJECTION_REASON}
        for _, body in client.posts
    )


def test_keep_latest_leaves_newest_awaiting_alone() -> None:
    incidents = [_incident("awaiting_approval", h) for h in (1, 2, 3, 4, 5)]
    client = FakeClient(incidents)
    _run(client, yes=True, keep_latest=2)
    newest_two = {incidents[0]["id"], incidents[1]["id"]}
    posted_ids = {path.split("/")[3] for path, _ in client.posts}
    assert len(posted_ids) == 3
    assert posted_ids.isdisjoint(newest_two)


def test_before_limits_by_age() -> None:
    incidents = [_incident("awaiting_approval", h) for h in (1, 10, 50, 100)]
    client = FakeClient(incidents)
    _run(client, yes=True, keep_latest=0, before=_NOW - timedelta(hours=24))
    posted_ids = {path.split("/")[3] for path, _ in client.posts}
    assert posted_ids == {incidents[2]["id"], incidents[3]["id"]}


def test_stops_on_first_error_and_reports_summary() -> None:
    client = FakeClient(_mixed_incidents(), fail_on_post=2)
    code, lines = _run(client, yes=True)
    assert code == 1
    assert len(client.posts) == 2
    assert lines[-1] == "Summary: rejected 2 of 147."


def test_http_client_refuses_any_non_reject_post() -> None:
    client = bulk.UrllibApiClient("https://example.invalid", "secret-key")
    with pytest.raises(ValueError, match="non-reject"):
        client.post_json(f"/internal/incidents/{uuid.uuid4()}/approve", {"approved_by": "x"})
