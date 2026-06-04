from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from datanorma.web import api_elt as elt_mod
from datanorma.web.deps import AuthUser, WorkspaceAuthContext, WorkspacePrincipal, get_conn, get_current_user, get_workspace_principal
from datanorma.web.main import create_app

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _stub_audit_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(elt_mod, "record_audit_event", lambda *_a, **_k: None)
    monkeypatch.setattr(elt_mod, "ensure_owner_manage_grant", lambda *_a, **_k: None)
    monkeypatch.setattr(elt_mod, "filter_rows_by_visibility", lambda _ctx, _conn, *, resource_type, rows: rows)


def _fake_principal() -> WorkspacePrincipal:
    user = AuthUser("seed_integrator", frozenset({"data_integrator"}), user_id=1)
    return WorkspacePrincipal(
        user=user,
        user_id=1,
        workspace_id=1,
        auth_ctx=WorkspaceAuthContext(user_id=1, workspace_id=1, is_admin=True),
    )


def _client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: AuthUser("seed_integrator", frozenset({"data_integrator"}), user_id=1)
    app.dependency_overrides[get_workspace_principal] = _fake_principal

    def _fake_conn():
        yield MagicMock()

    app.dependency_overrides[get_conn] = _fake_conn
    return TestClient(app)


def test_elt_sources_list(monkeypatch) -> None:
    with _client() as client:
        monkeypatch.setattr(elt_mod, "list_sources", lambda *_a, **_k: [{"id": 1, "config_encrypted": "{}"}])
        monkeypatch.setattr(
            elt_mod,
            "public_source_payload",
            lambda row: {"id": row["id"], "config": {}},
        )
        r = client.get("/api/v1/sources?workspace_code=main", headers={"X-Workspace-Id": "1"})
        assert r.status_code == 200
        assert r.json()["items"][0]["id"] == 1


def test_elt_sources_create(monkeypatch) -> None:
    with _client() as client:
        monkeypatch.setattr(
            elt_mod,
            "create_source_row",
            lambda *_a, **_k: {"id": 9, "config_encrypted": "{}", "workspace_id": 1, "name": "S", "connector_code": "ozon"},
        )
        monkeypatch.setattr(elt_mod, "public_source_payload", lambda row: {"id": row["id"], "config": {}})
        r = client.post(
            "/api/v1/sources",
            json={"name": "S", "connector_code": "ozon", "config": {}},
            headers={"X-Workspace-Id": "1"},
        )
        assert r.status_code == 201
        assert r.json()["item"]["id"] == 9


def test_elt_destinations_check_postgres_stub(monkeypatch) -> None:
    with _client() as client:
        monkeypatch.setattr(
            elt_mod,
            "get_destination",
            lambda *_a, **_k: {"id": 3, "connector_code": "postgres", "config_encrypted": "{}"},
        )
        monkeypatch.setattr(elt_mod, "touch_destination_checked", lambda *_a, **_k: None)
        from datanorma.destinations.base import DestinationCheckResult

        monkeypatch.setattr(
            elt_mod,
            "destination_check",
            lambda *_a, **_k: DestinationCheckResult(ok=True, message="ok", details={}),
        )
        r = client.post("/api/v1/destinations/3/check", headers={"X-Workspace-Id": "1"})
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True


def test_elt_connection_trigger_domain(monkeypatch) -> None:
    monkeypatch.setattr(elt_mod, "record_audit_event", lambda *_a, **_k: None)
    conn = MagicMock()
    conn.execute.return_value.mappings.return_value.first.return_value = {"id": 5, "source_id": 10}
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: AuthUser("seed_integrator", frozenset({"data_integrator"}), user_id=1)
    app.dependency_overrides[get_workspace_principal] = _fake_principal

    def _yield_conn():
        yield conn

    app.dependency_overrides[get_conn] = _yield_conn

    monkeypatch.setattr(
        elt_mod,
        "get_source",
        lambda *_a, **_k: {"id": 10, "connector_code": "ozon", "config_encrypted": "{}"},
    )
    monkeypatch.setattr(elt_mod, "create_sync_run", lambda *_a, **_k: {"id": 88, "status": "queued"})
    monkeypatch.setattr(
        elt_mod,
        "run_sync_inline_for_connection",
        lambda *_a, **_k: ({"id": 88, "status": "success", "dagster_run_id": "elt_inline"}, {"total_rows_written": 1, "streams": []}),
    )
    with TestClient(app) as client2:
        r = client2.post("/api/v1/connections/5/trigger", headers={"X-Workspace-Id": "1"})
        assert r.status_code == 202
        assert r.json()["run_id"] == 88
        assert r.json()["execution_mode"] == "inline"


def test_elt_connection_trigger_failure(monkeypatch) -> None:
    monkeypatch.setattr(elt_mod, "record_audit_event", lambda *_a, **_k: None)
    conn = MagicMock()
    conn.execute.return_value.mappings.return_value.first.return_value = {"id": 5, "source_id": 10}
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: AuthUser("seed_integrator", frozenset({"data_integrator"}), user_id=1)
    app.dependency_overrides[get_workspace_principal] = _fake_principal

    def _yield_conn():
        yield conn

    app.dependency_overrides[get_conn] = _yield_conn
    monkeypatch.setattr(elt_mod, "get_source", lambda *_a, **_k: {"id": 10, "connector_code": "ozon", "config_encrypted": "{}"})
    monkeypatch.setattr(elt_mod, "create_sync_run", lambda *_a, **_k: {"id": 99, "status": "queued"})
    monkeypatch.setattr(elt_mod, "run_sync_inline_for_connection", lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("sync failed")))
    with TestClient(app) as client2:
        r = client2.post("/api/v1/connections/5/trigger", headers={"X-Workspace-Id": "1"})
        assert r.status_code == 502
        assert r.json()["detail"]["error_code"] == "elt_sync_failed"
