"""Регистрация REST /api/data/destinations-catalog для React."""

from __future__ import annotations

from fastapi.routing import APIRoute

from datanorma.web.main import create_app


def test_destinations_catalog_route_registered() -> None:
    app = create_app()
    paths = {r.path for r in app.routes if isinstance(r, APIRoute)}
    assert "/api/data/destinations-catalog" in paths
