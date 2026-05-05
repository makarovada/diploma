from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from datanorma.web import api_elt as elt_mod
from datanorma.web.deps import AuthUser, get_conn, get_current_user
from datanorma.web.main import create_app

pytestmark = pytest.mark.integration


def test_elt_destinations_write_ok(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: AuthUser("seed_integrator", frozenset({"data_integrator"}))

    def _fake_conn():
        yield MagicMock()

    app.dependency_overrides[get_conn] = _fake_conn
    monkeypatch.setattr(elt_mod, "_wid", lambda *_a, **_k: 1)
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
        )
        assert r.status_code == 200
        assert r.json()["rows_written"] == 2
