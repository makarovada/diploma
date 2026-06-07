from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from datanorma.web import api_elt as elt_mod
from datanorma.web.deps import AuthUser, WorkspaceAuthContext, WorkspacePrincipal, get_conn, get_current_user, get_workspace_principal
from datanorma.web.main import create_app

pytestmark = pytest.mark.integration


def _fake_principal() -> WorkspacePrincipal:
    user = AuthUser("seed_integrator", frozenset({"data_integrator"}), user_id=1)
    return WorkspacePrincipal(
        user=user,
        user_id=1,
        workspace_id=1,
        auth_ctx=WorkspaceAuthContext(user_id=1, workspace_id=1, is_admin=True),
    )


def test_elt_destinations_write_ok(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: AuthUser("seed_integrator", frozenset({"data_integrator"}), user_id=1)
    app.dependency_overrides[get_workspace_principal] = _fake_principal

    def _fake_conn():
        yield MagicMock()

    app.dependency_overrides[get_conn] = _fake_conn
    monkeypatch.setattr(elt_mod, "record_audit_event", lambda *_a, **_k: None)
    monkeypatch.setattr(elt_mod, "ensure_owner_manage_grant", lambda *_a, **_k: None)
    monkeypatch.setattr(elt_mod, "filter_rows_by_visibility", lambda _ctx, _conn, *, resource_type, rows: rows)
    monkeypatch.setattr(
        elt_mod,
        "get_destination",
        lambda *_a, **_k: {"id": 7, "connector_code": "csv", "config_encrypted": "{}"},
    )
    from datanorma.destinations.base import DestinationWriteResult

    monkeypatch.setattr(
        elt_mod,
        "destination_write",
        lambda *_a, **_k: DestinationWriteResult(ok=True, message="ok", rows_written=2, details={}),
    )
    with TestClient(app) as client:
        r = client.post(
            "/api/v1/destinations/7/write",
            json={
                "workspace_code": "main",
                "stream_name": "t",
                "records": [{"a": 1}],
                "schema": {},
                "mode": "append",
            },
            headers={"X-Workspace-Id": "1"},
        )
        assert r.status_code == 200
        assert r.json()["rows_written"] == 2
