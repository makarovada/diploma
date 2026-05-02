from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from datanorma.web import api_router as api_mod
from datanorma.web.deps import AuthUser, get_conn, get_current_user
from datanorma.web.main import create_app
from datanorma.web.sync_runs import DagsterLaunchResult, SyncRunError


def _client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: AuthUser("seed_integrator", frozenset({"data_integrator"}))

    def _fake_conn():
        yield MagicMock()

    app.dependency_overrides[get_conn] = _fake_conn
    return TestClient(app)


def test_trigger_sync_launch_success(monkeypatch) -> None:
    with _client() as client:
        monkeypatch.setattr(api_mod, "resolve_connection", lambda *_a, **_k: (1, "ozon", "postings"))
        monkeypatch.setattr(
            api_mod,
            "create_sync_run",
            lambda *_a, **_k: {
                "id": 77,
                "status": "queued",
                "integration_code": "ozon",
                "stream_name": "postings",
            },
        )
        monkeypatch.setattr(
            api_mod,
            "launch_dagster_run",
            lambda *_a, **_k: DagsterLaunchResult(run_id="dagster-77", status="running"),
        )
        monkeypatch.setattr(
            api_mod,
            "mark_sync_run_running",
            lambda *_a, **_k: {"id": 77, "status": "running", "dagster_run_id": "dagster-77"},
        )

        resp = client.post("/api/v1/syncs/trigger", json={"connection_id": 1, "note": "smoke"})
        assert resp.status_code == 202
        data = resp.json()
        assert data["run_id"] == 77
        assert data["sync_run"]["status"] == "running"


def test_trigger_sync_launch_failed(monkeypatch) -> None:
    with _client() as client:
        monkeypatch.setattr(api_mod, "resolve_connection", lambda *_a, **_k: (1, "ozon", "postings"))
        monkeypatch.setattr(api_mod, "create_sync_run", lambda *_a, **_k: {"id": 12})
        monkeypatch.setattr(
            api_mod,
            "launch_dagster_run",
            lambda *_a, **_k: (_ for _ in ()).throw(SyncRunError("dagster is unavailable")),
        )
        monkeypatch.setattr(api_mod, "mark_sync_run_failed", lambda *_a, **_k: {"id": 12, "status": "failed"})

        resp = client.post("/api/v1/syncs/trigger", json={"connection_id": 1})
        assert resp.status_code == 502
        detail = resp.json()["detail"]
        assert detail["error_code"] == "dagster_launch_failed"
        assert detail["run_id"] == 12


def test_sync_status_endpoint_refreshes_run(monkeypatch) -> None:
    with _client() as client:
        monkeypatch.setattr(
            api_mod,
            "get_sync_run",
            lambda *_a, **_k: {"id": 5, "status": "running", "dagster_run_id": "dagster-5"},
        )
        monkeypatch.setattr(
            api_mod,
            "refresh_sync_run_status",
            lambda *_a, **_k: {
                "id": 5,
                "status": "success",
                "started_at": "2026-05-01T20:00:00+00:00",
                "finished_at": "2026-05-01T20:05:00+00:00",
                "error_message": None,
                "dagster_run_id": "dagster-5",
            },
        )
        resp = client.get("/api/v1/syncs/5/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["run_id"] == 5
        assert data["status"] == "success"
