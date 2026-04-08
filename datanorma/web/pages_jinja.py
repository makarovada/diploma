"""Фаза C: Jinja2-страницы веб-клиента (≥20 уникальных маршрутов /app/...)."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Any

import yaml
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from sqlalchemy.engine import Connection

import datanorma
from datanorma.config import get_settings
from datanorma.resources.paths import DataPathsResource
from datanorma.sources.registry import create_source
from datanorma.web.config import dagster_console_url
from datanorma.web.deps import AuthUser, get_conn
from datanorma.web.jwt_util import create_access_token
from datanorma.web.passwords import hash_password, verify_password
from datanorma.web.sql_util import warehouse_table_sql
from datanorma.web.users_repo import list_roles, list_users_with_roles, load_user_by_username
from datanorma.web.web_auth import COOKIE_NAME, get_web_user_optional, require_web_op

_TEMPLATES = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES))

router = APIRouter(prefix="/app", tags=["web-ui"])


def _safe_next(n: str) -> str:
    v = (n or "/app/dashboard").strip() or "/app/dashboard"
    return v if v.startswith("/app/") else "/app/dashboard"

# Навигация в духе Airbyte: секции Home / Build / Monitor / Settings / Access / Reference / Support.
NAV_GROUPS: list[tuple[str, list[tuple[str, str, str]]]] = [
    (
        "Home",
        [
            ("Home", "/app/dashboard", "view_sales_summary"),
            ("Analyst cabinet", "/app/analyst/cabinet", "view_analyst_cabinet"),
        ],
    ),
    (
        "Build",
        [
            ("Sources", "/app/sources", "view_dim_sources"),
            ("New Source", "/app/sources/new", "configure_new_source"),
            ("Source: Ozon", "/app/sources/ozon", "view_dim_sources"),
            ("Destinations", "/app/destinations", "view_destinations_page"),
            ("Connections", "/app/connections", "view_connections_overview"),
            ("Connections Builder", "/app/connections", "edit_connections_builder"),
            ("Stream catalog (mapping profiles)", "/app/mappings", "view_mapping_profiles"),
            ("Field mapping (YAML)", "/app/mappings/editor", "edit_mapping_profiles"),
        ],
    ),
    (
        "Monitor",
        [
            ("Sync history", "/app/runs", "view_pipeline_runs"),
            ("Sync job (sample)", "/app/runs/1", "view_pipeline_runs"),
            ("Normalization", "/app/monitoring/normalization", "view_normalization_issues"),
            ("Warehouse (table)", "/app/warehouse/sales", "view_sales_rows"),
            ("Export data", "/app/warehouse/export", "export_sales_csv"),
            ("Sample preview", "/app/samples/preview", "view_samples_preview"),
        ],
    ),
    (
        "Settings",
        [
            ("Secrets & configuration", "/app/integrations/secrets", "view_integration_config"),
            ("Replication schedule", "/app/settings/schedule", "edit_schedule_cron"),
            ("Connection graph", "/app/pipeline/graph", "view_pipeline_graph_static"),
        ],
    ),
    (
        "Access management",
        [
            ("Users", "/app/admin/users", "view_admin_users"),
            ("Member roles", "/app/admin/user-roles", "assign_user_roles"),
            ("Organizations & workspaces", "/app/workspaces", "view_workspaces"),
            ("Your password", "/app/account/password", "web_basic"),
        ],
    ),
    (
        "Reference data",
        [
            ("Source systems (catalog)", "/app/ref/source-systems", "view_dim_sources"),
            ("Currencies", "/app/ref/currencies", "view_dim_currencies"),
        ],
    ),
    (
        "Support",
        [
            ("About & FAQ", "/app/about", "web_basic"),
            ("Developer API (OpenAPI)", "/docs", "web_basic"),
            ("Orchestrator (Dagster)", "/app/external/dagster", "view_ops_console_hint"),
            ("Legacy UI", "/ui/", "web_basic"),
        ],
    ),
]


def _nav_groups_ctx(user: AuthUser) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for title, items in NAV_GROUPS:
        groups.append(
            {
                "title": title,
                "items": [{"label": a, "href": b, "allowed": user.can(c)} for a, b, c in items],
            }
        )
    return groups


def _ctx(request: Request, user: AuthUser, **kw: Any) -> dict[str, Any]:
    return {
        "request": request,
        "user": user,
        "nav_groups": _nav_groups_ctx(user),
        "dagster_url": dagster_console_url(),
        **kw,
    }


def _connection_cards(conn: Connection) -> list[dict[str, Any]]:
    """Логические «connections» как в Airbyte: source → destination."""
    specs = [
        ("ozon", "Ozon Seller API", "Ozon FBS → PostgreSQL (staging → canonical)"),
        ("1c", "1С (CSV/XLSX)", "1С → PostgreSQL (staging → canonical)"),
        ("google_sheet", "Google Sheets", "Sheets → PostgreSQL (staging → canonical)"),
    ]
    out: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)
    for code, source_name, flow in specs:
        row = conn.execute(
            text(
                "SELECT MAX(last_success_at) AS last_success_at FROM sync_state WHERE integration_code = :c"
            ),
            {"c": code},
        ).mappings().first()
        last = row["last_success_at"] if row and row["last_success_at"] else None
        badge = "muted"
        status_label = "Not yet synced"
        if last is not None:
            lu = last
            if getattr(lu, "tzinfo", None) is None:
                lu = lu.replace(tzinfo=timezone.utc)
            else:
                lu = lu.astimezone(timezone.utc)
            delta = now - lu
            if delta < timedelta(hours=48):
                badge = "success"
                status_label = "Healthy"
            else:
                badge = "warn"
                status_label = "Check sync"
        out.append(
            {
                "code": code,
                "source_name": source_name,
                "flow": flow,
                "last_sync": last,
                "badge": badge,
                "status_label": status_label,
            }
        )
    return out


def _repo_root() -> Path:
    return get_settings().resolved_repo_root()


def _samples_dir() -> Path:
    return get_settings().samples_dir()


def _mappings_yaml_path() -> Path:
    return get_settings().resolved_source_mappings_path()


def _default_connector_builder_yaml() -> str:
    p = Path(datanorma.__file__).resolve().parent / "schemas" / "connector_builder.yaml"
    return p.read_text(encoding="utf-8")


# --- auth ---


@router.get("/login")
def page_login(request: Request, next: str = "/app/dashboard"):
    n = _safe_next(next)
    u = get_web_user_optional(request)
    if u is not None:
        return RedirectResponse(n, status_code=302)
    return templates.TemplateResponse(
        request,
        "login.html",
        {"request": request, "next": n, "nav": []},
    )


@router.post("/login")
def page_login_post(
    request: Request,
    conn: Annotated[Connection, Depends(get_conn)],
    username: str = Form(),
    password: str = Form(),
    next: str = Form(default="/app/dashboard"),
):
    n = _safe_next(next)
    dbu = load_user_by_username(conn, username)
    if dbu is None or not verify_password(password, dbu.password_hash):
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "request": request,
                "error": "Неверный логин или пароль",
                "next": n,
                "nav": [],
            },
            status_code=401,
        )
    token = create_access_token(username=dbu.username, roles=dbu.roles)
    resp = RedirectResponse(n, status_code=302)
    resp.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
        path="/",
    )
    return resp


@router.get("/logout")
def page_logout():
    r = RedirectResponse("/app/login", status_code=302)
    r.delete_cookie(COOKIE_NAME, path="/")
    return r


# --- pages (каждый маршрут — отдельный экран для ВКР) ---


@router.get("/dashboard")
def page_dashboard(
    request: Request,
    user: Annotated[AuthUser, Depends(require_web_op("view_sales_summary"))],
    conn: Annotated[Connection, Depends(get_conn)],
):
    t = warehouse_table_sql()
    n = int(conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar_one())
    last = conn.execute(text(f"SELECT MAX(loaded_at) FROM {t}")).scalar()
    stg = {}
    if user.can("view_staging_counts"):
        stg = {
            "oz": int(conn.execute(text("SELECT COUNT(*) FROM raw_ozon_postings_staging")).scalar_one()),
            "c1": int(conn.execute(text("SELECT COUNT(*) FROM raw_1c_orders_staging")).scalar_one()),
            "sh": int(conn.execute(text("SELECT COUNT(*) FROM raw_google_sheet_orders_staging")).scalar_one()),
        }
    cards = _connection_cards(conn)
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        _ctx(
            request,
            user,
            row_count=n,
            max_loaded=last,
            staging=stg,
            connection_cards=cards,
            warehouse_table=t,
        ),
    )


@router.get("/connections")
def page_connections(
    request: Request,
    user: Annotated[AuthUser, Depends(require_web_op("view_connections_overview"))],
    conn: Annotated[Connection, Depends(get_conn)],
):
    cards = _connection_cards(conn)
    sync = conn.execute(
        text(
            "SELECT integration_code, stream_name, sync_mode, cursor_field, cursor_value, last_success_at "
            "FROM sync_state ORDER BY integration_code, stream_name"
        )
    ).mappings().all()
    runs = conn.execute(
        text(
            "SELECT id, job_name, status, started_at, finished_at, dagster_run_id "
            "FROM pipeline_run_summary ORDER BY id DESC LIMIT 15"
        )
    ).mappings().all()
    return templates.TemplateResponse(
        request,
        "connections.html",
        _ctx(
            request,
            user,
            connection_cards=cards,
            sync_rows=[dict(r) for r in sync],
            can_edit_connections=user.can("edit_connections_builder"),
            recent_runs=[dict(r) for r in runs],
        ),
    )


@router.post("/connections")
def page_connections_post(
    request: Request,
    user: Annotated[AuthUser, Depends(require_web_op("edit_connections_builder"))],
    conn: Annotated[Connection, Depends(get_conn)],
    integration_code: str = Form(),
    stream_name: str = Form(),
    sync_mode: str = Form(default="full_refresh"),
    cursor_field: str = Form(default=""),
):
    ic = integration_code.strip()
    sn = stream_name.strip()
    sm = sync_mode.strip() or "full_refresh"
    cf = cursor_field.strip() or None
    if not ic or not sn:
        raise HTTPException(status_code=400, detail="integration_code и stream_name обязательны")
    if sm not in ("full_refresh", "incremental"):
        raise HTTPException(status_code=400, detail="sync_mode должен быть full_refresh или incremental")

    cv = json.dumps({"cursor": None, "edited_via": "connections_builder"}, ensure_ascii=False)
    ajs = json.dumps({"cursor": None, "rows_emitted": 0, "edited_via": "connections_builder"}, ensure_ascii=False)
    conn.execute(
        text(
            "INSERT INTO sync_state (integration_code, stream_name, sync_mode, cursor_field, cursor_value, airbyte_state, last_success_at, updated_at) "
            "VALUES (:ic, :sn, :sm, :cf, :cv, CAST(:ajs AS jsonb), NOW(), NOW()) "
            "ON CONFLICT (integration_code, stream_name) DO UPDATE SET "
            "sync_mode = EXCLUDED.sync_mode, cursor_field = EXCLUDED.cursor_field, updated_at = NOW()"
        ),
        {"ic": ic, "sn": sn, "sm": sm, "cf": cf, "cv": cv, "ajs": ajs},
    )
    return RedirectResponse("/app/connections", status_code=303)


@router.get("/connections/sample/{code}")
def page_connection_sample(
    request: Request,
    code: str,
    user: Annotated[AuthUser, Depends(require_web_op("view_samples_preview"))],
    conn: Annotated[Connection, Depends(get_conn)],
):
    table_map = {
        "ozon": "raw_ozon_postings_staging",
        "1c": "raw_1c_orders_staging",
        "google_sheet": "raw_google_sheet_orders_staging",
    }
    table = table_map.get(code)
    if table is None:
        raise HTTPException(status_code=404, detail="Неизвестный source code")
    rows = conn.execute(
        text(
            f"SELECT id, _airbyte_extracted_at, _airbyte_meta, "
            + ("payload_json AS payload" if code == "ozon" else "row_json AS payload")
            + f" FROM {table} ORDER BY id DESC LIMIT 12"
        )
    ).mappings().all()
    blocks = [json.dumps(dict(r), ensure_ascii=False, indent=2, default=str) for r in rows]
    return templates.TemplateResponse(
        request,
        "samples_preview.html",
        _ctx(request, user, samples_dir=str(_samples_dir()), files=[], preview_lines=[], sample_blocks=blocks),
    )


@router.get("/destinations")
def page_destinations(
    request: Request,
    user: Annotated[AuthUser, Depends(require_web_op("view_destinations_page"))],
    conn: Annotated[Connection, Depends(get_conn)],
):
    t = warehouse_table_sql()
    n = int(conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar_one())
    return templates.TemplateResponse(
        request,
        "destinations.html",
        _ctx(
            request,
            user,
            warehouse_table=t,
            warehouse_rows=n,
        ),
    )


@router.get("/external/dagster")
def page_redirect_dagster(
    _: Annotated[AuthUser, Depends(require_web_op("view_ops_console_hint"))],
):
    return RedirectResponse(dagster_console_url(), status_code=302)


@router.get("/account/password")
def page_password_get(request: Request, user: Annotated[AuthUser, Depends(require_web_op("web_basic"))]):
    return templates.TemplateResponse(request, "account_password.html", _ctx(request, user))


@router.get("/analyst/cabinet")
def page_analyst_cabinet(
    request: Request,
    user: Annotated[AuthUser, Depends(require_web_op("view_analyst_cabinet"))],
    conn: Annotated[Connection, Depends(get_conn)],
):
    t = warehouse_table_sql()
    total_rows = int(conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar_one())
    by_source = conn.execute(
        text(f"SELECT source_system, COUNT(*) AS n FROM {t} GROUP BY source_system ORDER BY n DESC")
    ).mappings().all()
    workspaces = conn.execute(
        text(
            "SELECT o.code AS org_code, o.name AS org_name, w.code AS workspace_code, w.name AS workspace_name "
            "FROM app_user u "
            "JOIN user_workspace uw ON uw.user_id = u.id "
            "JOIN workspace w ON w.id = uw.workspace_id "
            "JOIN organization o ON o.id = w.organization_id "
            "WHERE u.username = :un "
            "ORDER BY o.code, w.code"
        ),
        {"un": user.username},
    ).mappings().all()
    return templates.TemplateResponse(
        request,
        "analyst_cabinet.html",
        _ctx(
            request,
            user,
            warehouse_table=t,
            total_rows=total_rows,
            by_source=[dict(r) for r in by_source],
            workspaces=[dict(r) for r in workspaces],
        ),
    )


@router.get("/workspaces")
def page_workspaces(
    request: Request,
    user: Annotated[AuthUser, Depends(require_web_op("view_workspaces"))],
    conn: Annotated[Connection, Depends(get_conn)],
):
    rows = conn.execute(
        text(
            "SELECT o.code AS org_code, o.name AS org_name, w.code AS workspace_code, w.name AS workspace_name "
            "FROM workspace w JOIN organization o ON o.id = w.organization_id "
            "ORDER BY o.code, w.code"
        )
    ).mappings().all()
    return templates.TemplateResponse(
        request,
        "workspaces.html",
        _ctx(request, user, rows=[dict(r) for r in rows], can_manage=user.can("manage_workspaces")),
    )


@router.post("/account/password")
def page_password_post(
    request: Request,
    user: Annotated[AuthUser, Depends(require_web_op("web_basic"))],
    conn: Annotated[Connection, Depends(get_conn)],
    old_password: str = Form(),
    new_password: str = Form(),
):
    dbu = load_user_by_username(conn, user.username)
    if dbu is None or not verify_password(old_password, dbu.password_hash):
        return templates.TemplateResponse(
            request,
            "account_password.html",
            _ctx(request, user, error="Текущий пароль неверен"),
            status_code=400,
        )
    if len(new_password) < 6:
        return templates.TemplateResponse(
            request,
            "account_password.html",
            _ctx(request, user, error="Новый пароль не короче 6 символов"),
            status_code=400,
        )
    conn.execute(
        text("UPDATE app_user SET password_hash = :h WHERE id = :id"),
        {"h": hash_password(new_password), "id": dbu.id},
    )
    return templates.TemplateResponse(request, "account_password.html", _ctx(request, user, ok="Пароль обновлён"))


@router.get("/sources")
def page_sources_list(
    request: Request,
    user: Annotated[AuthUser, Depends(require_web_op("view_dim_sources"))],
    conn: Annotated[Connection, Depends(get_conn)],
):
    rows = conn.execute(
        text("SELECT code, name, description FROM dim_source_system ORDER BY code")
    ).mappings().all()
    sync = conn.execute(
        text(
            "SELECT integration_code, stream_name, sync_mode, cursor_field, cursor_value, "
            "last_success_at FROM sync_state ORDER BY integration_code, stream_name"
        )
    ).mappings().all()
    return templates.TemplateResponse(
        request,
        "sources_list.html",
        _ctx(
            request,
            user,
            rows=[dict(r) for r in rows],
            sync_rows=[dict(r) for r in sync],
            can_configure_new_source=user.can("configure_new_source"),
        ),
    )


@router.get("/sources/new")
def page_sources_new_get(
    request: Request,
    user: Annotated[AuthUser, Depends(require_web_op("configure_new_source"))],
):
    kinds = [
        ("ozon", "Ozon Seller API"),
        ("1c", "1С (CSV/XLSX)"),
        ("google_sheet", "Google Sheets"),
        ("rest_builder", "REST API (Connector Builder YAML)"),
    ]
    return templates.TemplateResponse(
        request,
        "sources_new.html",
        _ctx(
            request,
            user,
            kinds=kinds,
            source_kind="ozon",
            yaml_default=_default_connector_builder_yaml(),
            yaml_body="",
            check_result=None,
            catalog_json=None,
            error=None,
        ),
    )


@router.post("/sources/new")
def page_sources_new_post(
    request: Request,
    user: Annotated[AuthUser, Depends(require_web_op("configure_new_source"))],
    source_kind: str = Form(),
    yaml_body: str = Form(default=""),
):
    kinds = [
        ("ozon", "Ozon Seller API"),
        ("1c", "1С (CSV/XLSX)"),
        ("google_sheet", "Google Sheets"),
        ("rest_builder", "REST API (Connector Builder YAML)"),
    ]
    check_result: dict[str, Any] | None = None
    catalog_json: str | None = None
    error: str | None = None
    paths = DataPathsResource()
    try:
        sk = source_kind.strip()
        yaml_text = yaml_body.strip() if sk == "rest_builder" else None
        if sk == "rest_builder" and not yaml_text:
            yaml_text = _default_connector_builder_yaml()
        src = create_source(sk, paths=paths, yaml_text=yaml_text)
        cr = src.check()
        det = cr.details or {}
        check_result = {
            "ok": cr.ok,
            "message": cr.message,
            "details_text": json.dumps(det, ensure_ascii=False, indent=2) if det else "",
        }
        catalog = src.discover()
        catalog_json = json.dumps(catalog.model_dump(mode="json"), ensure_ascii=False, indent=2)
    except Exception as exc:
        error = str(exc)
    return templates.TemplateResponse(
        request,
        "sources_new.html",
        _ctx(
            request,
            user,
            kinds=kinds,
            source_kind=source_kind.strip() or "ozon",
            yaml_default=_default_connector_builder_yaml(),
            yaml_body=yaml_body,
            check_result=check_result,
            catalog_json=catalog_json,
            error=error,
        ),
    )


@router.get("/sources/{code}")
def page_source_detail(
    request: Request,
    code: str,
    user: Annotated[AuthUser, Depends(require_web_op("view_dim_sources"))],
    conn: Annotated[Connection, Depends(get_conn)],
):
    row = conn.execute(
        text("SELECT code, name, description FROM dim_source_system WHERE code = :c"),
        {"c": code},
    ).mappings().first()
    sync_rows = conn.execute(
        text("SELECT * FROM sync_state WHERE integration_code = :c ORDER BY stream_name"),
        {"c": code},
    ).mappings().all()
    if row is None:
        raise HTTPException(status_code=404, detail="Источник не найден")
    sync_blocks = [
        json.dumps(dict(r), ensure_ascii=False, indent=2, default=str) for r in sync_rows
    ]
    return templates.TemplateResponse(
        request,
        "source_detail.html",
        _ctx(request, user, row=dict(row), sync_blocks=sync_blocks),
    )


@router.get("/integrations/secrets")
def page_secrets_get(
    request: Request,
    user: Annotated[AuthUser, Depends(require_web_op("view_integration_config"))],
    conn: Annotated[Connection, Depends(get_conn)],
):
    rows = conn.execute(
        text("SELECT id, config_key, config_value, is_secret, updated_at FROM integration_config ORDER BY id")
    ).mappings().all()
    safe = []
    for r in rows:
        d = dict(r)
        if d.get("is_secret") and d.get("config_value"):
            d["config_value"] = "***"
        safe.append(d)
    can_edit = user.can("edit_integration_config")
    return templates.TemplateResponse(
        request,
        "integrations_secrets.html",
        _ctx(request, user, rows=safe, can_edit=can_edit),
    )


@router.post("/integrations/secrets")
def page_secrets_post(
    request: Request,
    user: Annotated[AuthUser, Depends(require_web_op("edit_integration_config"))],
    conn: Annotated[Connection, Depends(get_conn)],
    config_key: str = Form(),
    config_value: str = Form(default=""),
    is_secret: str = Form(default=""),
):
    sec = is_secret in ("on", "true", "1")
    conn.execute(
        text("INSERT INTO integration_config (config_key, config_value, is_secret) VALUES (:k, :v, :s)"),
        {"k": config_key.strip(), "v": config_value, "s": sec},
    )
    return RedirectResponse("/app/integrations/secrets", status_code=303)


@router.get("/mappings")
def page_mappings(
    request: Request,
    user: Annotated[AuthUser, Depends(require_web_op("view_mapping_profiles"))],
    conn: Annotated[Connection, Depends(get_conn)],
):
    rows = conn.execute(
        text("SELECT id, name, version, notes, created_at FROM mapping_profile ORDER BY id")
    ).mappings().all()
    return templates.TemplateResponse(
        request,
        "mappings_list.html",
        _ctx(request, user, rows=[dict(r) for r in rows]),
    )


@router.get("/mappings/editor")
def page_mappings_editor_get(
    request: Request,
    user: Annotated[AuthUser, Depends(require_web_op("edit_mapping_profiles"))],
):
    path = _mappings_yaml_path()
    text_content = path.read_text(encoding="utf-8") if path.is_file() else "# файл не найден"
    mappings_obj: dict[str, Any] = {}
    try:
        mappings_obj = yaml.safe_load(text_content) or {}
    except Exception:
        mappings_obj = {}
    return templates.TemplateResponse(
        request,
        "mappings_editor.html",
        _ctx(
            request,
            user,
            path=str(path),
            yaml_content=text_content,
            mappings_json=json.dumps(mappings_obj, ensure_ascii=False),
        ),
    )


@router.post("/mappings/editor")
def page_mappings_editor_post(
    request: Request,
    user: Annotated[AuthUser, Depends(require_web_op("edit_mapping_profiles"))],
    yaml_content: str = Form(default=""),
):
    note = "В прототипе изменения не пишутся на диск: используйте GitOps / IDE. Показана отправленная копия."
    mappings_obj: dict[str, Any] = {}
    try:
        mappings_obj = yaml.safe_load(yaml_content) or {}
        if not isinstance(mappings_obj, dict):
            mappings_obj = {}
            note = "YAML разобран, но корень не объект. Показана исходная копия."
    except Exception as exc:
        note = f"Ошибка YAML: {exc}. Показана исходная копия."
    return templates.TemplateResponse(
        request,
        "mappings_editor.html",
        _ctx(
            request,
            user,
            path=str(_mappings_yaml_path()),
            yaml_content=yaml_content,
            note=note,
            mappings_json=json.dumps(mappings_obj, ensure_ascii=False),
        ),
    )


@router.get("/samples/preview")
def page_samples(
    request: Request,
    user: Annotated[AuthUser, Depends(require_web_op("view_samples_preview"))],
):
    d = _samples_dir()
    files = []
    if d.is_dir():
        for p in sorted(d.glob("*")):
            if p.is_file():
                files.append({"name": p.name, "size": p.stat().st_size})
    preview_lines: list[str] = []
    sample_csv = d / "1c_export.csv"
    if sample_csv.is_file():
        with sample_csv.open(encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if i >= 12:
                    break
                preview_lines.append(line.rstrip("\n"))
    return templates.TemplateResponse(
        request,
        "samples_preview.html",
        _ctx(request, user, samples_dir=str(d), files=files, preview_lines=preview_lines, sample_blocks=[]),
    )


@router.get("/runs")
def page_runs(
    request: Request,
    user: Annotated[AuthUser, Depends(require_web_op("view_pipeline_runs"))],
    conn: Annotated[Connection, Depends(get_conn)],
):
    rows = conn.execute(
        text(
            "SELECT id, dagster_run_id, job_name, status, started_at, finished_at FROM pipeline_run_summary "
            "ORDER BY id DESC LIMIT 80"
        )
    ).mappings().all()
    return templates.TemplateResponse(
        request,
        "runs_list.html",
        _ctx(request, user, rows=[dict(r) for r in rows]),
    )


@router.get("/runs/{run_id:int}")
def page_run_detail(
    request: Request,
    run_id: int,
    user: Annotated[AuthUser, Depends(require_web_op("view_pipeline_runs"))],
    conn: Annotated[Connection, Depends(get_conn)],
):
    row = conn.execute(
        text("SELECT * FROM pipeline_run_summary WHERE id = :id"),
        {"id": run_id},
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Run не найден")
    row_json = json.dumps(dict(row), ensure_ascii=False, indent=2, default=str)
    return templates.TemplateResponse(request, "run_detail.html", _ctx(request, user, row_json=row_json))


@router.get("/pipeline/graph")
def page_graph(
    request: Request,
    user: Annotated[AuthUser, Depends(require_web_op("view_pipeline_graph_static"))],
):
    return templates.TemplateResponse(
        request,
        "pipeline_graph.html",
        _ctx(request, user, dagster_url=dagster_console_url()),
    )


@router.get("/warehouse/sales")
def page_warehouse(
    request: Request,
    user: Annotated[AuthUser, Depends(require_web_op("view_sales_rows"))],
    conn: Annotated[Connection, Depends(get_conn)],
    source_system: str = "",
    limit: int = 50,
):
    t = warehouse_table_sql()
    lim = max(1, min(limit, 500))
    ss = source_system.strip()
    if ss:
        rows = conn.execute(
            text(
                f"SELECT source_system, source_record_id, event_datetime, amount, amount_rub, currency_code, "
                f"channel, status, loaded_at FROM {t} WHERE source_system = :ss "
                f"ORDER BY loaded_at DESC NULLS LAST LIMIT :lim"
            ),
            {"ss": ss, "lim": lim},
        ).mappings().all()
    else:
        rows = conn.execute(
            text(
                f"SELECT source_system, source_record_id, event_datetime, amount, amount_rub, currency_code, "
                f"channel, status, loaded_at FROM {t} ORDER BY loaded_at DESC NULLS LAST LIMIT :lim"
            ),
            {"lim": lim},
        ).mappings().all()
    return templates.TemplateResponse(
        request,
        "warehouse_sales.html",
        _ctx(
            request,
            user,
            rows=[dict(r) for r in rows],
            filter_source=ss,
            limit=lim,
            table=t,
        ),
    )


@router.get("/warehouse/export")
def page_export_html(
    request: Request,
    user: Annotated[AuthUser, Depends(require_web_op("export_sales_csv"))],
):
    return templates.TemplateResponse(request, "warehouse_export.html", _ctx(request, user))


@router.get("/warehouse/download.csv")
def page_export_csv(
    request: Request,
    user: Annotated[AuthUser, Depends(require_web_op("export_sales_csv"))],
    conn: Annotated[Connection, Depends(get_conn)],
    limit: int = 5000,
):
    t = warehouse_table_sql()
    lim = max(1, min(limit, 5000))
    rows = conn.execute(
        text(
            f"SELECT source_system, source_record_id, event_datetime, amount, amount_rub, currency_code, "
            f"channel, status, loaded_at FROM {t} ORDER BY loaded_at DESC NULLS LAST LIMIT :lim"
        ),
        {"lim": lim},
    ).mappings().all()
    cols = [
        "source_system",
        "source_record_id",
        "event_datetime",
        "amount",
        "amount_rub",
        "currency_code",
        "channel",
        "status",
        "loaded_at",
    ]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(cols)
    for r in rows:
        w.writerow([r[c] for c in cols])
    data = buf.getvalue()
    return StreamingResponse(
        iter([data]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="canonical_sales.csv"'},
    )


@router.get("/ref/currencies")
def page_ref_curr(
    request: Request,
    user: Annotated[AuthUser, Depends(require_web_op("view_dim_currencies"))],
    conn: Annotated[Connection, Depends(get_conn)],
):
    rows = conn.execute(text("SELECT code, name FROM dim_currency ORDER BY code")).mappings().all()
    return templates.TemplateResponse(
        request,
        "ref_currencies.html",
        _ctx(request, user, rows=[dict(r) for r in rows]),
    )


@router.get("/ref/source-systems")
def page_ref_sources(
    request: Request,
    user: Annotated[AuthUser, Depends(require_web_op("view_dim_sources"))],
    conn: Annotated[Connection, Depends(get_conn)],
):
    rows = conn.execute(
        text("SELECT code, name, description FROM dim_source_system ORDER BY code")
    ).mappings().all()
    return templates.TemplateResponse(
        request,
        "ref_sources.html",
        _ctx(request, user, rows=[dict(r) for r in rows]),
    )


@router.get("/admin/users")
def page_admin_users(
    request: Request,
    user: Annotated[AuthUser, Depends(require_web_op("view_admin_users"))],
    conn: Annotated[Connection, Depends(get_conn)],
):
    users = list_users_with_roles(conn)
    return templates.TemplateResponse(request, "admin_users.html", _ctx(request, user, users=users))


@router.get("/admin/user-roles")
def page_user_roles_get(
    request: Request,
    user: Annotated[AuthUser, Depends(require_web_op("assign_user_roles"))],
    conn: Annotated[Connection, Depends(get_conn)],
):
    users = list_users_with_roles(conn)
    roles = list_roles(conn)
    return templates.TemplateResponse(
        request,
        "admin_user_roles.html",
        _ctx(request, user, users=users, roles=roles),
    )


@router.post("/admin/user-roles")
def page_user_roles_post(
    request: Request,
    user: Annotated[AuthUser, Depends(require_web_op("assign_user_roles"))],
    conn: Annotated[Connection, Depends(get_conn)],
    user_id: int = Form(),
    role_id: int = Form(),
    action: str = Form(default="add"),
):
    if action == "remove":
        conn.execute(
            text("DELETE FROM user_role WHERE user_id = :u AND role_id = :r"),
            {"u": user_id, "r": role_id},
        )
    else:
        conn.execute(
            text(
                "INSERT INTO user_role (user_id, role_id) VALUES (:u, :r) "
                "ON CONFLICT (user_id, role_id) DO NOTHING"
            ),
            {"u": user_id, "r": role_id},
        )
    return RedirectResponse("/app/admin/user-roles", status_code=303)


@router.get("/monitoring/normalization")
def page_norm(
    request: Request,
    user: Annotated[AuthUser, Depends(require_web_op("view_normalization_issues"))],
    conn: Annotated[Connection, Depends(get_conn)],
):
    rows = conn.execute(
        text(
            "SELECT id, batch_id, source_system, source_record_id, field_name, issue_type, message, created_at "
            "FROM normalization_issue ORDER BY id DESC LIMIT 100"
        )
    ).mappings().all()
    return templates.TemplateResponse(
        request,
        "monitoring_norm.html",
        _ctx(request, user, rows=[dict(r) for r in rows]),
    )


@router.get("/settings/schedule")
def page_schedule_get(
    request: Request,
    user: Annotated[AuthUser, Depends(require_web_op("edit_schedule_cron"))],
    conn: Annotated[Connection, Depends(get_conn)],
):
    row = conn.execute(
        text("SELECT config_value FROM integration_config WHERE config_key = :k"),
        {"k": "datanorma.schedule_cron"},
    ).mappings().first()
    cron = row["config_value"] if row else "0 5 * * *"
    return templates.TemplateResponse(
        request,
        "settings_schedule.html",
        _ctx(request, user, cron=cron or ""),
    )


@router.post("/settings/schedule")
def page_schedule_post(
    request: Request,
    user: Annotated[AuthUser, Depends(require_web_op("edit_schedule_cron"))],
    conn: Annotated[Connection, Depends(get_conn)],
    cron: str = Form(),
):
    key = "datanorma.schedule_cron"
    conn.execute(
        text("DELETE FROM integration_config WHERE config_key = :k"),
        {"k": key},
    )
    conn.execute(
        text("INSERT INTO integration_config (config_key, config_value, is_secret) VALUES (:k, :v, false)"),
        {"k": key, "v": cron.strip()},
    )
    return RedirectResponse("/app/settings/schedule", status_code=303)


@router.get("/about")
def page_about(request: Request, user: Annotated[AuthUser, Depends(require_web_op("web_basic"))]):
    web_ops = [entry[2] for _, items in NAV_GROUPS for entry in items]
    matrix = yaml.safe_dump(
        {
            "операции_веб": web_ops,
            "dagster": dagster_console_url(),
        },
        allow_unicode=True,
        default_flow_style=False,
    )
    return templates.TemplateResponse(request, "about_help.html", _ctx(request, user, matrix_hint=matrix))
