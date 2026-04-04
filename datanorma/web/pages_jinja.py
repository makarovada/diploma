"""Фаза C: Jinja2-страницы веб-клиента (≥20 уникальных маршрутов /app/...)."""

from __future__ import annotations

import csv
import io
import os
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
        ],
    ),
    (
        "Build",
        [
            ("Sources", "/app/sources", "view_dim_sources"),
            ("Source: Ozon", "/app/sources/ozon", "view_dim_sources"),
            ("Destinations", "/app/destinations", "view_destinations_page"),
            ("Connections", "/app/connections", "view_connections_overview"),
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
                "SELECT last_success_at, updated_at FROM sync_state WHERE integration_code = :c"
            ),
            {"c": code},
        ).mappings().first()
        last = row["last_success_at"] if row else None
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
    env = os.environ.get("DATANORMA_REPO_ROOT", "").strip()
    if env:
        return Path(env)
    return Path(datanorma.__file__).resolve().parent.parent


def _samples_dir() -> Path:
    env = os.environ.get("DATANORMA_REPO_ROOT", "").strip()
    if env:
        return Path(env) / "data" / "samples"
    return _repo_root() / "data" / "samples"


def _mappings_yaml_path() -> Path:
    p = os.environ.get("DATANORMA_SOURCE_MAPPINGS_PATH", "").strip()
    if p:
        return Path(p)
    return Path(datanorma.__file__).resolve().parent / "schemas" / "source_mappings.yaml"


# --- auth ---


@router.get("/login")
def page_login(request: Request, next: str = "/app/dashboard"):
    n = _safe_next(next)
    u = get_web_user_optional(request)
    if u is not None:
        return RedirectResponse(n, status_code=302)
    return templates.TemplateResponse(
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
            "oz": int(conn.execute(text("SELECT COUNT(*) FROM raw_ozon_staging")).scalar_one()),
            "c1": int(conn.execute(text("SELECT COUNT(*) FROM raw_1c_staging")).scalar_one()),
            "sh": int(conn.execute(text("SELECT COUNT(*) FROM raw_sheet_staging")).scalar_one()),
        }
    cards = _connection_cards(conn)
    return templates.TemplateResponse(
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
    runs = conn.execute(
        text(
            "SELECT id, job_name, status, started_at, finished_at, dagster_run_id "
            "FROM pipeline_run_summary ORDER BY id DESC LIMIT 15"
        )
    ).mappings().all()
    return templates.TemplateResponse(
        "connections.html",
        _ctx(
            request,
            user,
            connection_cards=cards,
            recent_runs=[dict(r) for r in runs],
        ),
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
    return templates.TemplateResponse("account_password.html", _ctx(request, user))


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
            "account_password.html",
            _ctx(request, user, error="Текущий пароль неверен"),
            status_code=400,
        )
    if len(new_password) < 6:
        return templates.TemplateResponse(
            "account_password.html",
            _ctx(request, user, error="Новый пароль не короче 6 символов"),
            status_code=400,
        )
    conn.execute(
        text("UPDATE app_user SET password_hash = :h WHERE id = :id"),
        {"h": hash_password(new_password), "id": dbu.id},
    )
    return templates.TemplateResponse("account_password.html", _ctx(request, user, ok="Пароль обновлён"))


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
        text("SELECT integration_code, cursor_value, last_success_at FROM sync_state ORDER BY integration_code")
    ).mappings().all()
    return templates.TemplateResponse(
        "sources_list.html",
        _ctx(request, user, rows=[dict(r) for r in rows], sync_rows=[dict(r) for r in sync]),
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
    sync = conn.execute(
        text("SELECT * FROM sync_state WHERE integration_code = :c"),
        {"c": code},
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Источник не найден")
    sync_json = json.dumps(dict(sync), ensure_ascii=False, indent=2, default=str) if sync else ""
    return templates.TemplateResponse(
        "source_detail.html",
        _ctx(request, user, row=dict(row), sync_json=sync_json),
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
    return templates.TemplateResponse(
        "mappings_editor.html",
        _ctx(request, user, path=str(path), yaml_content=text_content),
    )


@router.post("/mappings/editor")
def page_mappings_editor_post(
    request: Request,
    user: Annotated[AuthUser, Depends(require_web_op("edit_mapping_profiles"))],
    yaml_content: str = Form(default=""),
):
    return templates.TemplateResponse(
        "mappings_editor.html",
        _ctx(
            request,
            user,
            path=str(_mappings_yaml_path()),
            yaml_content=yaml_content,
            note="В прототипе изменения не пишутся на диск: используйте GitOps / IDE. Показана отправленная копия.",
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
        "samples_preview.html",
        _ctx(request, user, samples_dir=str(d), files=files, preview_lines=preview_lines),
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
    return templates.TemplateResponse("run_detail.html", _ctx(request, user, row_json=row_json))


@router.get("/pipeline/graph")
def page_graph(
    request: Request,
    user: Annotated[AuthUser, Depends(require_web_op("view_pipeline_graph_static"))],
):
    return templates.TemplateResponse(
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
    return templates.TemplateResponse("warehouse_export.html", _ctx(request, user))


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
    return templates.TemplateResponse("admin_users.html", _ctx(request, user, users=users))


@router.get("/admin/user-roles")
def page_user_roles_get(
    request: Request,
    user: Annotated[AuthUser, Depends(require_web_op("assign_user_roles"))],
    conn: Annotated[Connection, Depends(get_conn)],
):
    users = list_users_with_roles(conn)
    roles = list_roles(conn)
    return templates.TemplateResponse(
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
    matrix = yaml.safe_dump(
        {
            "операции_веб": [x[2] for x in NAV_ITEMS],
            "dagster": dagster_console_url(),
        },
        allow_unicode=True,
        default_flow_style=False,
    )
    return templates.TemplateResponse("about_help.html", _ctx(request, user, matrix_hint=matrix))
