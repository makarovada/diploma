"""Фаза C: достаточно уникальных маршрутов /app/* (без БД)."""

from __future__ import annotations

import pytest
from fastapi.routing import APIRoute

from datanorma.web.main import create_app

pytestmark = pytest.mark.integration


def test_at_least_20_unique_app_paths() -> None:
    app = create_app()
    paths = {r.path for r in app.routes if isinstance(r, APIRoute) and r.path.startswith("/app/")}
    assert len(paths) >= 20, f"Ожидалось ≥20 путей /app/*, сейчас {len(paths)}"
    assert "/app/warehouse/download.csv" in paths
    assert "/app/warehouse/download.json" in paths
    assert "/app/warehouse/download.xml" in paths
    assert "/app/warehouse/download.xlsx" in paths


def test_unauthenticated_app_dashboard_redirects() -> None:
    from fastapi.testclient import TestClient

    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        r = client.get("/app/dashboard", follow_redirects=False)
        assert r.status_code in (302, 307)
        assert "/app/login" in (r.headers.get("location") or "")
