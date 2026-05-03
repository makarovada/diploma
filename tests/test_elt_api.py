from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from datanorma.web import api_elt as elt_mod
from datanorma.web.deps import AuthUser, get_conn, get_current_user
from datanorma.web.main import create_app


def _client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: AuthUser("seed_integrator", frozenset({"data_integrator"}))

    def _fake_conn():
        yield MagicMock()

    app.dependency_overrides[get_conn] = _fake_conn
    return TestClient(app)


def test_elt_sources_list(monkeypatch) -> None:
    with _client() as client:
        monkeypatch.setattr(elt_mod, "_wid", lambda *_a, **_k: 1)
        monkeypatch.setattr(elt_mod, "list_sources", lambda *_a, **_k: [{"id": 1, "config_encrypted": "{}"}])
        monkeypatch.setattr(
            elt_mod,
            "public_source_payload",
            lambda row: {"id": row["id"], "config": {}},
        )
        r = client.get("/api/v1/sources?workspace_code=main")
        assert r.status_code == 200
        assert r.json()["items"][0]["id"] == 1


def test_elt_sources_create(monkeypatch) -> None:
    with _client() as client:
        monkeypatch.setattr(elt_mod, "_wid", lambda *_a, **_k: 1)
        monkeypatch.setattr(
            elt_mod,
            "create_source_row",
            lambda *_a, **_k: {"id": 9, "config_encrypted": "{}", "workspace_id": 1, "name": "S", "connector_code": "ozon"},
        )
        monkeypatch.setattr(elt_mod, "public_source_payload", lambda row: {"id": row["id"], "config": {}})
        r = client.post("/api/v1/sources", json={"name": "S", "connector_code": "ozon", "config": {}})
        assert r.status_code == 201
        assert r.json()["item"]["id"] == 9


def test_elt_destinations_check_postgres_stub(monkeypatch) -> None:
    with _client() as client:
        monkeypatch.setattr(elt_mod, "_wid", lambda *_a, **_k: 1)
        monkeypatch.setattr(
            elt_mod,
            "get_destination",
            lambda *_a, **_k: {"id": 3, "connector_code": "postgres", "config_encrypted": "{}"},
        )
        monkeypatch.setattr(elt_mod, "touch_destination_checked", lambda *_a, **_k: None)

        class _Eng:
            def connect(self):
                return self

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def execute(self, *_a, **_k):
                return None

        monkeypatch.setattr(elt_mod, "create_engine", lambda *_a, **_k: _Eng())
        r = client.post("/api/v1/destinations/3/check")
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True


def test_elt_connection_trigger_domain(monkeypatch) -> None:
    monkeypatch.setattr(elt_mod, "_wid", lambda *_a, **_k: 1)
    conn = MagicMock()
    conn.execute.return_value.first.return_value = (1,)
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: AuthUser("seed_integrator", frozenset({"data_integrator"}))

    def _yield_conn():
        yield conn

    app.dependency_overrides[get_conn] = _yield_conn
    from datanorma.web.sync_runs import DagsterLaunchResult

    monkeypatch.setattr(elt_mod, "resolve_connection", lambda *_a, **_k: (10, 5, "ozon", "postings"))
    monkeypatch.setattr(elt_mod, "create_sync_run", lambda *_a, **_k: {"id": 88, "status": "queued"})
    monkeypatch.setattr(
        elt_mod,
        "launch_dagster_run",
        lambda *_a, **_k: DagsterLaunchResult(run_id="x", status="running"),
    )
    monkeypatch.setattr(
        elt_mod,
        "mark_sync_run_running",
        lambda *_a, **_k: {"id": 88, "status": "running"},
    )
    with TestClient(app) as client2:
        r = client2.post("/api/v1/connections/5/trigger")
        assert r.status_code == 202
        assert r.json()["run_id"] == 88
