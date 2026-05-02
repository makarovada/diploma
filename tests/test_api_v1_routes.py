from __future__ import annotations

from fastapi.routing import APIRoute

from datanorma.web.main import create_app


def test_api_v1_routes_registered() -> None:
    app = create_app()
    paths = {r.path for r in app.routes if isinstance(r, APIRoute)}
    assert "/api/v1/connections" in paths
    assert "/api/v1/syncs" in paths
    assert "/api/v1/syncs/trigger" in paths
    assert "/api/v1/syncs/{run_id}" in paths
    assert "/api/v1/syncs/{run_id}/status" in paths
    assert "/api/v1/workspaces" in paths
