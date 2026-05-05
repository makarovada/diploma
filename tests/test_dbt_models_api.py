from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from datanorma.web.deps import AuthUser, get_conn, get_current_user
from datanorma.web.main import create_app

pytestmark = pytest.mark.integration


def test_v1_dbt_models_returns_items_and_source_flag() -> None:
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: AuthUser("seed_analyst", frozenset({"analyst"}))

    def _fake_conn():
        yield MagicMock()

    app.dependency_overrides[get_conn] = _fake_conn
    with TestClient(app) as client:
        r = client.get("/api/v1/dbt/models")
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert body["source"] in ("manifest", "sql")
    names = {item["name"] for item in body["items"]}
    assert "yandex_metrika_visits" in names
