"""REST /api/data/destinations-catalog для React SPA."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from datanorma.web.deps import AuthUser, get_conn, get_current_user
from datanorma.web.main import create_app

pytestmark = pytest.mark.unit


class _ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value


def test_destinations_catalog_route_registered() -> None:
    app = create_app()
    paths = {r.path for r in app.routes if isinstance(r, APIRoute)}
    assert "/api/data/destinations-catalog" in paths


def test_destinations_catalog_returns_items(monkeypatch: pytest.MonkeyPatch) -> None:
    """Smoke: handler не падает (регрессия NameError warehouse_row_count)."""
    from datanorma.web import api_router as api_mod

    monkeypatch.setattr(api_mod, "warehouse_row_count", lambda _conn: 0)
    monkeypatch.setattr(
        api_mod,
        "list_destinations",
        lambda _conn, workspace_id: [
            {
                "id": 1,
                "name": "Test dest",
                "connector_code": "postgres",
                "status": "active",
                "config": {"schema": "public", "table_name": "orders"},
                "updated_at": None,
                "last_checked_at": None,
            }
        ],
    )
    monkeypatch.setattr(
        api_mod,
        "public_destination_payload",
        lambda row: {
            "id": row["id"],
            "name": row["name"],
            "connector_code": row["connector_code"],
            "status": row["status"],
            "config": row["config"],
            "updated_at": row.get("updated_at"),
            "last_checked_at": row.get("last_checked_at"),
        },
    )
    monkeypatch.setattr(api_mod, "resolve_effective_workspace_id", lambda _conn, _user, _wid: 1)

    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: AuthUser(
        "seed_admin", frozenset({"platform_admin"}), user_id=1
    )
    conn = MagicMock()
    conn.execute.return_value = _ScalarResult(0)

    def _fake_conn():
        yield conn

    app.dependency_overrides[get_conn] = _fake_conn

    with TestClient(app) as client:
        r = client.get("/api/data/destinations-catalog?workspace_code=main")

    assert r.status_code == 200
    body = r.json()
    assert body["warehouse_row_count"] == 0
    assert len(body["items"]) == 1
    assert body["items"][0]["name"] == "Test dest"
