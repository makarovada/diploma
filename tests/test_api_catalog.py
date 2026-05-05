from __future__ import annotations

from fastapi.routing import APIRoute

from datanorma.web.main import create_app

import pytest

pytestmark = pytest.mark.unit


def test_connectors_catalog_routes_registered() -> None:
    app = create_app()
    paths = {r.path for r in app.routes if isinstance(r, APIRoute)}
    assert "/api/v1/connectors/catalog" in paths
    assert "/api/v1/connectors/catalog/{code}" in paths

