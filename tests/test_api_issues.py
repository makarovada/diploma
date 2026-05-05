from __future__ import annotations

from fastapi.routing import APIRoute

from datanorma.web.main import create_app

import pytest

pytestmark = pytest.mark.unit


def test_issues_routes_registered() -> None:
    app = create_app()
    paths = {r.path for r in app.routes if isinstance(r, APIRoute)}
    assert "/api/v1/issues" in paths
    assert "/api/v1/issues/{issue_id}" in paths
    assert "/api/v1/issues/export" in paths

