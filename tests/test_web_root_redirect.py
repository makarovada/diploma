"""Корневой URL ведёт на React SPA (/ui/), Jinja остаётся на /app/*."""

from __future__ import annotations

from fastapi.testclient import TestClient

from datanorma.web.main import create_app


def test_root_redirects_to_ui_spa() -> None:
    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        r = client.get("/", follow_redirects=False)
        assert r.status_code in (302, 307)
        loc = r.headers.get("location") or ""
        assert "/ui/" in loc
