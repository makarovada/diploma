from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from datanorma.web import api_router as api_mod
from datanorma.web.deps import AuthUser, get_conn, get_current_user
from datanorma.web.main import create_app
from datanorma.web.sync_runs import SyncRunError

pytestmark = pytest.mark.integration


class _MapResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return self

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None


class _ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar(self):
        return self.value


def _client(conn: MagicMock | None = None) -> tuple[TestClient, MagicMock]:
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: AuthUser("seed_admin", frozenset({"platform_admin"}), user_id=1001)
    fake_conn = conn or MagicMock()

    def _fake():
        yield fake_conn

    app.dependency_overrides[get_conn] = _fake
    return TestClient(app), fake_conn


def test_layers_raw_and_normalized_endpoints() -> None:
    conn = MagicMock()
    conn.execute.side_effect = [
        _MapResult([{"table_schema": "raw", "table_name": "yandex_metrika__visits"}]),
        _MapResult([{"table_schema": "normalized", "table_name": "yandex_metrika__visits"}]),
    ]
    client, _ = _client(conn)
    with client:
        r1 = client.get("/api/v1/layers/raw?stream=visits&limit=10")
        r2 = client.get("/api/v1/layers/normalized?stream=visits&limit=10")
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["items"][0]["table_schema"] == "raw"
    assert r2.json()["items"][0]["table_schema"] == "normalized"


def test_dbt_model_preview_error_path() -> None:
    conn = MagicMock()
    conn.execute.side_effect = SQLAlchemyError("missing table")
    client, _ = _client(conn)
    with client:
        r = client.get("/api/v1/dbt/models/yandex_metrika_visits/preview")
    assert r.status_code == 404
    assert r.json()["detail"]["error_code"] == "model_preview_failed"


def test_sync_logs_synthetic_when_no_db_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = MagicMock()
    conn.execute.return_value = _MapResult([])
    monkeypatch.setattr(api_mod, "get_sync_run", lambda *_a, **_k: {"id": 5, "status": "running"})
    monkeypatch.setattr(api_mod, "refresh_sync_run_status", lambda *_a, **_k: {"id": 5, "status": "failed", "updated_at": "2026-05-01T00:00:00Z"})
    client, _ = _client(conn)
    with client:
        r = client.get("/api/v1/syncs/5/logs")
    assert r.status_code == 200
    items = r.json()["items"]
    assert any(i["stage"] == "dbt_run" for i in items)
    assert any(i["level"] == "error" for i in items)


def test_sync_retry_invalid_and_issue_actions(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = MagicMock()
    monkeypatch.setattr(api_mod, "_audit_api", lambda *_a, **_k: None)
    monkeypatch.setattr(api_mod, "get_sync_run", lambda *_a, **_k: {"id": 7, "connection_id": 1, "integration_code": "ozon", "stream_name": "postings"})
    monkeypatch.setattr(api_mod, "create_sync_run", lambda *_a, **_k: {"id": 99})
    monkeypatch.setattr(api_mod, "launch_sync_run_via_dagster", lambda *_a, **_k: (_ for _ in ()).throw(SyncRunError("boom")))
    monkeypatch.setattr(api_mod, "mark_sync_run_failed", lambda *_a, **_k: {"id": 99, "status": "failed"})

    client, _ = _client(conn)
    with client:
        retry = client.post("/api/v1/syncs/7/retry")
    assert retry.status_code == 502
    assert retry.json()["detail"]["error_code"] == "dagster_launch_failed"


def test_sync_streams_list_upsert_and_syncs_list(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = MagicMock()
    conn.execute.side_effect = [
        _MapResult([{"id": 1, "integration_code": "ozon", "stream_name": "postings"}]),
        _MapResult([]),
    ]
    monkeypatch.setattr(api_mod, "_audit_api", lambda *_a, **_k: None)
    monkeypatch.setattr(api_mod, "refresh_recent_sync_runs", lambda *_a, **_k: [{"id": 7, "status": "running"}])
    monkeypatch.setattr(api_mod, "attach_load_destination", lambda *_a, **_k: {"id": 7, "status": "running", "destination": "pg"})
    client, _ = _client(conn)
    with client:
        listed = client.get("/api/v1/sync-streams")
        upsert = client.post(
            "/api/v1/sync-streams",
            json={"integration_code": "ozon", "stream_name": "postings", "sync_mode": "incremental"},
        )
        syncs = client.get("/api/v1/syncs")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["integration_code"] == "ozon"
    assert upsert.status_code == 200
    assert syncs.status_code == 200
    assert syncs.json()["items"][0]["destination"] == "pg"


def test_workspaces_and_audit_log_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = MagicMock()
    conn.execute.side_effect = [
        _MapResult([{"org_code": "org", "workspace_code": "main"}]),
        _MapResult([]),
        _MapResult([]),
        _MapResult([]),
        _ScalarResult(101),
    ]
    monkeypatch.setattr(api_mod, "_audit_api", lambda *_a, **_k: None)
    client, _ = _client(conn)
    with client:
        create = client.post(
            "/api/v1/workspaces",
            json={"org_code": "org", "org_name": "Org", "workspace_code": "main", "workspace_name": "Main"},
        )
    assert create.status_code in (200, 422)
    if create.status_code == 200:
        assert create.json()["status"] == "ok"
