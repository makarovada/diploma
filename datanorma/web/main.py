"""FastAPI: REST API, статический SPA (/ui) и Jinja2 веб-клиент (/app)."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from datanorma.web.api_router import router as api_router
from datanorma.web.pages_jinja import router as pages_router
from datanorma.web.pages_jinja import templates as jinja_templates
from datanorma.web.web_auth import WebAuthRequired

_STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app() -> FastAPI:
    app = FastAPI(
        title="DataNorma",
        description="Прототип: REST API, JWT/RBAC, Jinja2 веб-клиент (фаза C).",
        version="0.3.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix="/api")
    app.include_router(pages_router)

    @app.exception_handler(WebAuthRequired)
    async def _web_auth(_request: Request, exc: WebAuthRequired) -> RedirectResponse:
        nxt = quote(exc.path or "/app/dashboard", safe="")
        return RedirectResponse(f"/app/login?next={nxt}", status_code=302)

    @app.exception_handler(HTTPException)
    async def _http403_html(request: Request, exc: HTTPException):
        if exc.status_code == 403 and request.url.path.startswith("/app/"):
            detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
            return jinja_templates.TemplateResponse(
                request,
                "forbidden.html",
                {"request": request, "detail": detail, "nav": []},
                status_code=403,
            )
        return await http_exception_handler(request, exc)

    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse(url="/app/login")

    if _STATIC_DIR.is_dir():
        app.mount("/ui", StaticFiles(directory=str(_STATIC_DIR), html=True), name="ui")

    return app


app = create_app()
