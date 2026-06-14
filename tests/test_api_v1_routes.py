from __future__ import annotations

import pytest
from fastapi.routing import APIRoute

from datanorma.web.main import create_app

pytestmark = pytest.mark.unit


def test_api_v1_routes_registered() -> None:
    app = create_app()
    paths = {r.path for r in app.routes if isinstance(r, APIRoute)}
    assert "/api/v1/sync-streams" in paths
    assert "/api/v1/connections" in paths
    assert "/api/v1/sources" in paths
    assert "/api/v1/destinations" in paths
    assert "/api/v1/syncs" in paths
    assert "/api/v1/syncs/trigger" in paths
    assert "/api/v1/syncs/{run_id}" in paths
    assert "/api/v1/syncs/{run_id}/status" in paths
    assert "/api/v1/syncs/{run_id}/logs" in paths
    assert "/api/v1/syncs/{run_id}/issues" in paths
    assert "/api/v1/syncs/{run_id}/retry" in paths
    assert "/api/v1/syncs/{run_id}/cancel" in paths
    assert "/api/v1/issues/{issue_id}/resolve" in paths
    assert "/api/v1/issues/{issue_id}/ignore" in paths
    assert "/api/v1/workspaces" in paths
    assert "/api/v1/audit-log" in paths
    assert "/api/v1/dbt/models" in paths
    assert "/api/v1/dbt/models/{model_name}/preview" in paths
