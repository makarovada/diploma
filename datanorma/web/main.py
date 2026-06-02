"""FastAPI: REST API и статический SPA (/ui)."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from datanorma.web.api_router import router as api_router
from datanorma.web.config import cors_allow_origins, validate_security_at_startup
from datanorma.web.connection_scheduler import start_connection_scheduler, stop_connection_scheduler


def _resolve_ui_static_dir() -> Path | None:
    """Сборка React из Docker кладётся в /app/client/dist; в репозитории — демо в datanorma/web/static."""
    override = (os.environ.get("DATANORMA_UI_STATIC_DIR") or "").strip()
    if override:
        p = Path(override)
        if p.is_dir() and (p / "index.html").is_file():
            return p
    docker_dist = Path("/app/client/dist")
    if docker_dist.is_dir() and (docker_dist / "index.html").is_file():
        return docker_dist
    bundled = Path(__file__).resolve().parent / "static"
    if bundled.is_dir():
        return bundled
    return None


@asynccontextmanager
async def _app_lifespan(_app: FastAPI):
    start_connection_scheduler()
    try:
        yield
    finally:
        stop_connection_scheduler()


def create_app() -> FastAPI:
    validate_security_at_startup()
    app = FastAPI(
        title="DataNorma",
        description="REST API, JWT/RBAC; UI — React SPA (/ui/).",
        version="0.3.0",
        lifespan=_app_lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_allow_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix="/api")

    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse(url="/ui/")

    static_dir = _resolve_ui_static_dir()
    if static_dir is not None:
        app.mount("/ui", StaticFiles(directory=str(static_dir), html=True), name="ui")

    return app


app = create_app()
