from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from datanorma.destinations.base import DestinationWriteResult
from datanorma.web import api_elt as elt_mod
from datanorma.web.deps import AuthUser, WorkspaceAuthContext, WorkspacePrincipal, get_conn, get_current_user, get_workspace_principal
from datanorma.web.elt_repo import EltRepoError
from datanorma.web.main import create_app

pytestmark = pytest.mark.integration

_WS_HEADERS = {"X-Workspace-Id": "1"}


def _fake_principal() -> WorkspacePrincipal:
    user = AuthUser("seed_admin", frozenset({"platform_admin"}), user_id=1)
    return WorkspacePrincipal(
        user=user,
        user_id=1,
        workspace_id=1,
        auth_ctx=WorkspaceAuthContext(user_id=1, workspace_id=1, is_admin=True),
    )


def _client(conn: MagicMock | None = None) -> tuple[TestClient, MagicMock]:
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: AuthUser("seed_admin", frozenset({"platform_admin"}), user_id=1)
    app.dependency_overrides[get_workspace_principal] = _fake_principal
    fake_conn = conn or MagicMock()

    def _fake_conn():
        yield fake_conn

    app.dependency_overrides[get_conn] = _fake_conn
    return TestClient(app), fake_conn


@pytest.fixture(autouse=True)
def _stub_audit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(elt_mod, "record_audit_event", lambda *_a, **_k: None)
    monkeypatch.setattr(elt_mod, "ensure_owner_manage_grant", lambda *_a, **_k: None)
    monkeypatch.setattr(elt_mod, "filter_rows_by_visibility", lambda _ctx, _conn, *, resource_type, rows: rows)


def test_sources_check_requires_yaml_for_rest_builder(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(elt_mod, "get_source", lambda *_a, **_k: {"id": 1, "connector_code": "rest_builder", "config_encrypted": "{}"})
    monkeypatch.setattr(elt_mod, "public_source_payload", lambda _r: {"id": 1, "config": {}})
    client, _ = _client()
    with client:
        r = client.post("/api/v1/sources/1/check", headers=_WS_HEADERS)
    assert r.status_code == 422
    assert r.json()["detail"]["error_code"] == "config_invalid"


def test_sources_discover_unknown_connector(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(elt_mod, "get_source", lambda *_a, **_k: {"id": 2, "connector_code": "custom_unknown", "config_encrypted": "{}"})
    monkeypatch.setattr(elt_mod, "public_source_payload", lambda _r: {"id": 2, "config": {}})
    monkeypatch.setattr(elt_mod, "create_source", lambda *_a, **_k: (_ for _ in ()).throw(ValueError("unknown")))
    client, _ = _client()
    with client:
        r = client.post("/api/v1/sources/2/discover", headers=_WS_HEADERS)
    assert r.status_code == 422
    assert r.json()["detail"]["error_code"] == "unknown_connector"


def test_destination_write_failed_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(elt_mod, "get_destination", lambda *_a, **_k: {"id": 7, "connector_code": "csv", "config_encrypted": "{}"})
    monkeypatch.setattr(elt_mod, "public_destination_payload", lambda _r: {"id": 7, "config": {"path": "x.csv"}})
    monkeypatch.setattr(
        elt_mod,
        "destination_write",
        lambda *_a, **_k: DestinationWriteResult(ok=False, message="cannot write", rows_written=0, details={"reason": "bad"}),
    )
    client, _ = _client()
    with client:
        r = client.post(
            "/api/v1/destinations/7/write",
            json={"stream_name": "orders", "records": [{"id": 1}], "stream_schema": {"type": "object"}, "mode": "append"},
            headers=_WS_HEADERS,
        )
    assert r.status_code == 422
    assert r.json()["detail"]["error_code"] == "destination_write_failed"


def test_connections_create_and_pause_resume_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        elt_mod,
        "create_connection_row",
        lambda *_a, **_k: (_ for _ in ()).throw(EltRepoError("invalid link")),
    )
    monkeypatch.setattr(elt_mod, "update_connection_row", lambda *_a, **_k: None)
    client, _ = _client()
    with client:
        create = client.post(
            "/api/v1/connections",
            json={"name": "C1", "source_id": 1, "destination_id": 1, "streams": []},
            headers=_WS_HEADERS,
        )
        pause = client.post("/api/v1/connections/12/pause", headers=_WS_HEADERS)
        resume = client.post("/api/v1/connections/12/resume", headers=_WS_HEADERS)
    assert create.status_code == 422
    assert create.json()["detail"]["error_code"] == "invalid_connection"
    assert pause.status_code == 404
    assert resume.status_code == 404


def test_source_delete_conflict_when_in_use(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = MagicMock()
    conn.execute.return_value.scalar_one.return_value = 2
    client, _ = _client(conn)
    with client:
        r = client.delete("/api/v1/sources/9", headers=_WS_HEADERS)
    assert r.status_code == 409
    assert r.json()["detail"]["error_code"] == "source_in_use"


def test_destinations_delete_conflict_and_unknown_check(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = MagicMock()
    conn.execute.return_value.scalar_one.return_value = 1
    client, _ = _client(conn)
    with client:
        conflict = client.delete("/api/v1/destinations/4", headers=_WS_HEADERS)
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["error_code"] == "destination_in_use"

    monkeypatch.setattr(elt_mod, "get_destination", lambda *_a, **_k: {"id": 4, "connector_code": "unknown", "config_encrypted": "{}"})
    monkeypatch.setattr(elt_mod, "public_destination_payload", lambda _r: {"id": 4, "config": {}})
    monkeypatch.setattr(elt_mod, "touch_destination_checked", lambda *_a, **_k: None)
    monkeypatch.setattr(elt_mod, "destination_check", lambda *_a, **_k: (_ for _ in ()).throw(ValueError("no dest")))
    client2, _ = _client()
    with client2:
        bad = client2.post("/api/v1/destinations/4/check", headers=_WS_HEADERS)
    assert bad.status_code == 422
    assert bad.json()["detail"]["error_code"] == "unknown_destination"


def test_connections_get_patch_delete_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(elt_mod, "get_connection", lambda *_a, **_k: None)
    monkeypatch.setattr(elt_mod, "update_connection_row", lambda *_a, **_k: None)
    monkeypatch.setattr(elt_mod, "patch_connection_row", lambda *_a, **_k: None)
    monkeypatch.setattr(elt_mod, "delete_connection_row", lambda *_a, **_k: False)
    client, _ = _client()
    with client:
        g = client.get("/api/v1/connections/77", headers=_WS_HEADERS)
        p = client.patch("/api/v1/connections/77", json={"status": "paused"}, headers=_WS_HEADERS)
        d = client.delete("/api/v1/connections/77", headers=_WS_HEADERS)
    assert g.status_code == 404
    assert p.status_code == 404
    assert d.status_code == 404


def test_connections_trigger_elt_inline(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = MagicMock()
    conn.execute.return_value.mappings.return_value.first.return_value = {"id": 5, "source_id": 10}
    monkeypatch.setattr(
        elt_mod,
        "get_source",
        lambda *_a, **_k: {"id": 10, "connector_code": "google_sheet", "config_encrypted": "{}"},
    )
    monkeypatch.setattr(
        elt_mod,
        "create_sync_run",
        lambda *_a, **_k: {"id": 100, "status": "queued"},
    )
    monkeypatch.setattr(
        elt_mod,
        "run_sync_inline_for_connection",
        lambda *_a, **_k: ({"id": 100, "status": "success"}, {"total_rows_written": 2, "streams": []}),
    )
    client, _ = _client(conn)
    with client:
        r = client.post("/api/v1/connections/5/trigger", headers=_WS_HEADERS)
    assert r.status_code == 202
    body = r.json()
    assert body["run_id"] == 100
    assert body["summary"]["total_rows_written"] == 2
