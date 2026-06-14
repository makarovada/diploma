from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from datanorma.web import api_router as api_mod
from datanorma.web.deps import AuthUser, get_conn, get_current_user
from datanorma.web.main import create_app

pytestmark = pytest.mark.integration


def _client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: AuthUser("seed_integrator", frozenset({"data_integrator"}))

    def _fake_conn():
        yield MagicMock()

    app.dependency_overrides[get_conn] = _fake_conn
    return TestClient(app)


def test_mapping_profiles_draft_save(monkeypatch) -> None:
    with _client() as client:
        monkeypatch.setattr(api_mod, "resolve_workspace_id", lambda *_a, **_k: 1)
        monkeypatch.setattr(
            api_mod,
            "create_draft_version",
            lambda *_a, **_k: {"id": 11, "profile_id": 7, "version": 2, "status": "draft"},
        )
        payload = {
            "workspace_code": "main",
            "source_type": "google_sheet",
            "stream_name": "orders",
            "profile_name": "default",
            "rules_json": {"handler": "column_map", "stream": "orders", "fields": {"Номер": "source_record_id"}},
        }
        r = client.post("/api/data/mapping-profiles/draft", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["item"]["status"] == "draft"


def test_mapping_profiles_activate(monkeypatch) -> None:
    with _client() as client:
        monkeypatch.setattr(
            api_mod,
            "activate_profile_version",
            lambda *_a, **_k: {"id": 7, "active_version_id": 11, "is_active": True},
        )
        r = client.post("/api/data/mapping-profiles/activate", json={"profile_id": 7, "version_id": 11})
        assert r.status_code == 200
        assert r.json()["item"]["is_active"] is True


def test_mapping_profiles_list_versions(monkeypatch) -> None:
    with _client() as client:
        monkeypatch.setattr(api_mod, "list_versions", lambda *_a, **_k: [{"id": 11, "version": 2, "status": "published"}])
        r = client.get("/api/data/mapping-profiles/7/versions")
        assert r.status_code == 200
        assert r.json()["rows"][0]["status"] == "published"
