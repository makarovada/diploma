"""Корневой URL перенаправляет на React SPA (/ui/)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from datanorma.web.main import create_app

pytestmark = pytest.mark.integration


def test_root_redirects_to_ui_spa() -> None:
    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        r = client.get("/", follow_redirects=False)
        assert r.status_code in (302, 307)
        loc = r.headers.get("location") or ""
        assert "/ui/" in loc
