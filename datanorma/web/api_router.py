"""REST API: логин, данные, админка — на каждом маршруте проверка операции RBAC."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError

from datanorma.config import get_settings
from datanorma.web.config import dagster_console_url
from datanorma.web.audit_repo import list_audit_log, record_audit_event
from datanorma.web.deps import (
    AuthUser,
    get_conn,
    get_current_user,
    get_engine_cached,
    require_operation,
    require_permission,
    require_request_workspace_id,
    resolve_actor_user_id,
    resolve_effective_workspace_id,
)
from datanorma.web.request_audit import client_ip, client_user_agent
from datanorma.web.jwt_util import create_access_token
from datanorma.web.mapping_profiles import (
    MappingProfileError,
    activate_profile_version,
    create_draft_version,
    list_profiles,
    list_versions,
    publish_version,
    resolve_workspace_id,
    rollback_to_version,
)
from datanorma.web.passwords import hash_password, is_legacy_sha256_hash, verify_password
from datanorma.web.permission_catalog import PERM_AUDIT_READ, PERM_CONNECTION_UPDATE
from datanorma.web.deps import WorkspacePrincipal, get_workspace_principal
from datanorma.web.permission_service import effective_permissions_for_user
from datanorma.web.api_workspaces import register_workspace_routes
from datanorma.web.api_resource_grants import register_resource_grant_routes
from datanorma.web.sync_launch import build_sync_audit_payload, launch_sync_run_via_dagster, run_sync_inline_for_connection
from datanorma.web.sync_runs import (
    SyncRunError,
    attach_load_destination,
    create_sync_run,
    get_sync_run,
    mark_sync_run_failed,
    refresh_recent_sync_runs,
    refresh_sync_run_status,
    resolve_connection,
)
from datanorma.web.norm_issues import list_norm_issues_for_run, list_norm_issues_for_workspace
from datanorma.web.api_v1_catalog import register_api_v1_catalog_routes
from datanorma.web.api_elt import get_elt_workspace_id, register_elt_routes
from datanorma.web.elt_repo import list_destinations, public_destination_payload
from datanorma.web.sql_util import warehouse_row_count
from datanorma.web.workspace_repo import create_workspace
from datanorma.web.users_repo import (
    assign_role_to_user,
    create_user,
    list_all_workspace_ids,
    list_roles,
    list_users_with_roles,
    load_user_by_username,
    load_user_workspaces,
    load_workspaces_visible,
    update_user_password_hash,
)

router = APIRouter(tags=["api"])
v1 = APIRouter(prefix="/v1", tags=["api-v1"])


def _audit_api(
    conn: Connection,
    request: Request | None,
    user: AuthUser,
    *,
    workspace_id: int | None,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    result: str = "success",
    payload: dict[str, Any] | None = None,
) -> None:
    record_audit_event(
        get_engine_cached(),
        workspace_id=workspace_id,
        actor_user_id=resolve_actor_user_id(conn, user),
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        result=result,
        payload=payload,
        ip_address=client_ip(request),
        user_agent=client_user_agent(request),
    )


def _mapping_profile_workspace_id(conn: Connection, profile_id: int) -> int | None:
    row = conn.execute(
        text("SELECT workspace_id FROM mapping_profile WHERE id = :id"),
        {"id": profile_id},
    ).scalar()
    return int(row) if row is not None else None


_DBT_CONFIG_SCHEMA_RE = re.compile(r"schema\s*=\s*['\"]([a-zA-Z_][\w]*)['\"]", re.IGNORECASE)
_DBT_CONFIG_MATERIALIZED_RE = re.compile(r"materialized\s*=\s*['\"]([a-zA-Z_][\w]*)['\"]", re.IGNORECASE)
_DBT_SOURCE_RE = re.compile(r"source\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)", re.IGNORECASE)
_SAFE_IDENT_RE = re.compile(r"^[a-z_][a-z0-9_]*$")


def _dbt_models_dir() -> Path:
    return get_settings().resolved_repo_root() / "dbt" / "models"


def _dbt_manifest_path() -> Path:
    return get_settings().resolved_repo_root() / "dbt" / "target" / "manifest.json"


def _parse_sql_select_columns(sql_text: str) -> list[dict[str, Any]]:
    """Извлечь имена колонок из верхнего SELECT … FROM (без подзапросов в типовых dbt-моделях)."""
    m = re.search(r"(?is)\bselect\b\s*(.+?)\s*\bfrom\b", sql_text)
    if not m:
        return []
    block = m.group(1)
    cols: list[dict[str, Any]] = []
    for mm in re.finditer(r"\bAS\s+([a-zA-Z_][a-zA-Z0-9_]*)\b", block):
        cols.append(
            {
                "name": mm.group(1),
                "dataType": "unknown",
                "description": "",
                "isPrimaryKey": False,
            }
        )
    return cols


def _models_from_manifest() -> list[dict[str, Any]] | None:
    p = _dbt_manifest_path()
    if not p.is_file():
        return None
    try:
        manifest = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    repo_root = get_settings().resolved_repo_root()
    items: list[dict[str, Any]] = []
    for _uid, node in manifest.get("nodes", {}).items():
        if not isinstance(node, dict) or node.get("resource_type") != "model":
            continue
        name = str(node.get("name") or "").strip()
        if not name:
            continue
        schema = str(node.get("schema") or "semantic")
        description = str(node.get("description") or "").strip()
        cfg = node.get("config") if isinstance(node.get("config"), dict) else {}
        materialized_as = str((cfg or {}).get("materialized") or "table")
        ofp = str(node.get("original_file_path") or "").replace("\\", "/")
        domain = "other"
        if "models/" in ofp:
            tail = ofp.split("models/", 1)[1]
            segs = tail.split("/")
            if len(segs) > 1:
                domain = segs[0]
        columns: list[dict[str, Any]] = []
        raw_cols = node.get("columns")
        if isinstance(raw_cols, dict):
            for col_name, col in raw_cols.items():
                if not isinstance(col, dict):
                    continue
                meta = col.get("meta") if isinstance(col.get("meta"), dict) else {}
                columns.append(
                    {
                        "name": str(col.get("name") or col_name),
                        "dataType": str(col.get("data_type") or "unknown"),
                        "description": str(col.get("description") or ""),
                        "isPrimaryKey": bool((meta or {}).get("primary_key")),
                    }
                )
        sources: list[str] = []
        depends = node.get("depends_on")
        if isinstance(depends, dict):
            for dep in depends.get("nodes") or []:
                if not isinstance(dep, str) or not dep.startswith("source."):
                    continue
                parts = dep.split(".")
                if len(parts) >= 4:
                    sources.append(f"{parts[-2]}.{parts[-1]}")
        rel_path = ofp
        if ofp:
            try:
                candidate = repo_root / ofp
                if candidate.is_file():
                    rel_path = str(candidate.relative_to(repo_root)).replace("\\", "/")
            except ValueError:
                rel_path = ofp
        items.append(
            {
                "name": name,
                "schema": schema,
                "materialized_as": materialized_as,
                "sources": sources,
                "domain": domain,
                "path": rel_path,
                "description": description,
                "columns": columns,
            }
        )
    items.sort(key=lambda x: (x["domain"], x["name"]))
    return items


def _models_from_sql_scan() -> list[dict[str, Any]]:
    models_dir = _dbt_models_dir()
    if not models_dir.is_dir():
        return []
    repo_root = get_settings().resolved_repo_root()
    items: list[dict[str, Any]] = []
    for path in sorted(models_dir.rglob("*.sql")):
        sql_text = path.read_text(encoding="utf-8")
        schema, materialized_as, sources = _parse_dbt_model_sql(sql_text)
        name = path.stem
        items.append(
            {
                "name": name,
                "schema": schema,
                "materialized_as": materialized_as,
                "sources": sources,
                "domain": path.parent.name,
                "path": str(path.relative_to(repo_root)).replace("\\", "/"),
                "description": "",
                "columns": _parse_sql_select_columns(sql_text),
            }
        )
    return items


def _parse_dbt_model_sql(sql_text: str) -> tuple[str, str, list[str]]:
    schema = "semantic"
    materialized_as = "table"
    schema_match = _DBT_CONFIG_SCHEMA_RE.search(sql_text)
    if schema_match:
        schema = schema_match.group(1)
    materialized_match = _DBT_CONFIG_MATERIALIZED_RE.search(sql_text)
    if materialized_match:
        materialized_as = materialized_match.group(1)
    sources = [f"{sm.group(1)}.{sm.group(2)}" for sm in _DBT_SOURCE_RE.finditer(sql_text)]
    return schema, materialized_as, sources


def _safe_ident(value: str, field: str) -> str:
    if not _SAFE_IDENT_RE.match(value):
        raise HTTPException(status_code=422, detail={"error_code": "invalid_identifier", "field": field})
    return value


class LoginBody(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


class RegisterBody(BaseModel):
    username: str = Field(min_length=3, max_length=128, pattern=r"^[a-zA-Z0-9._-]+$")
    email: str | None = Field(default=None, max_length=255)
    password: str = Field(min_length=8, max_length=256)
    registration_mode: str = Field(pattern="^(create_workspace|wait_for_invite)$")
    workspace_name: str | None = Field(default=None, min_length=1, max_length=255)
    workspace_code: str | None = Field(default=None, min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9_-]*$")


@router.post("/auth/login")
def auth_login(
    body: LoginBody,
    request: Request,
    conn: Annotated[Connection, Depends(get_conn)],
) -> dict[str, str]:
    eng = get_engine_cached()
    ip = client_ip(request)
    ua = client_user_agent(request)
    user = load_user_by_username(conn, body.username)
    if user is None or not verify_password(body.password, user.password_hash):
        record_audit_event(
            eng,
            workspace_id=None,
            actor_user_id=user.id if user else None,
            action="login_failure",
            resource_type="auth",
            resource_id=body.username.strip()[:128],
            result="failure",
            payload={"reason": "invalid_credentials"},
            ip_address=ip,
            user_agent=ua,
        )
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    if is_legacy_sha256_hash(user.password_hash):
        update_user_password_hash(conn, user.id, hash_password(body.password))
    member_ws = load_user_workspaces(conn, user.id)
    allowed_ids = [w["id"] for w in member_ws]
    if not allowed_ids:
        record_audit_event(
            eng,
            workspace_id=None,
            actor_user_id=user.id,
            action="login_denied_no_workspace",
            resource_type="auth",
            resource_id=user.username,
            result="failure",
            payload={"reason": "no_workspace"},
            ip_address=ip,
            user_agent=ua,
        )
        raise HTTPException(status_code=403, detail="Нет доступных workspace для пользователя")
    active_wid = allowed_ids[0]
    token = create_access_token(
        username=user.username,
        roles=user.roles,
        user_id=user.id,
        active_workspace_id=active_wid,
        allowed_workspace_ids=allowed_ids,
    )
    record_audit_event(
        eng,
        workspace_id=active_wid,
        actor_user_id=user.id,
        action="login_success",
        resource_type="auth",
        resource_id=user.username,
        result="success",
        payload={"active_workspace_id": active_wid},
        ip_address=ip,
        user_agent=ua,
    )
    return {"access_token": token, "token_type": "bearer"}


@router.post("/auth/register", status_code=status.HTTP_201_CREATED)
def auth_register(
    body: RegisterBody,
    request: Request,
    conn: Annotated[Connection, Depends(get_conn)],
) -> dict[str, Any]:
    username = body.username.strip()
    if load_user_by_username(conn, username) is not None:
        raise HTTPException(
            status_code=409,
            detail={"error_code": "username_exists", "message": "Пользователь с таким логином уже существует"},
        )

    try:
        user_id = create_user(
            conn,
            username=username,
            email=(body.email or "").strip() or None,
            password_hash=hash_password(body.password),
        )
    except Exception as exc:
        if "unique" in str(exc).lower():
            raise HTTPException(
                status_code=409,
                detail={"error_code": "username_exists", "message": "Пользователь с таким логином уже существует"},
            ) from exc
        raise

    assign_role_to_user(conn, user_id=user_id, role_name="analyst")
    workspace: dict[str, Any] | None = None
    if body.registration_mode == "create_workspace":
        ws_code = (body.workspace_code or "").strip() or username.lower().replace(".", "-")
        ws_name = (body.workspace_name or "").strip() or f"Workspace {username}"
        try:
            workspace = create_workspace(
                conn,
                code=ws_code,
                name=ws_name,
                created_by_user_id=user_id,
            )
        except Exception as exc:
            if "uq_workspace" in str(exc).lower() or "unique" in str(exc).lower():
                raise HTTPException(
                    status_code=409,
                    detail={"error_code": "workspace_code_exists", "message": "Код пространства уже занят"},
                ) from exc
            raise

    record_audit_event(
        get_engine_cached(),
        workspace_id=int(workspace["id"]) if workspace else None,
        actor_user_id=user_id,
        action="register_success",
        resource_type="auth",
        resource_id=username,
        result="success",
        payload={
            "registration_mode": body.registration_mode,
            "workspace_id": int(workspace["id"]) if workspace else None,
        },
        ip_address=client_ip(request),
        user_agent=client_user_agent(request),
    )
    return {
        "status": "ok",
        "registration_mode": body.registration_mode,
        "user": {"id": user_id, "username": username},
        "workspace": (
            {"id": int(workspace["id"]), "code": str(workspace["code"]), "name": str(workspace["name"])}
            if workspace
            else None
        ),
        "message": (
            "Аккаунт создан, ожидайте добавления в существующий workspace."
            if body.registration_mode == "wait_for_invite"
            else "Аккаунт и workspace созданы."
        ),
    }


@router.get("/auth/me")
def auth_me(
    user: Annotated[AuthUser, Depends(get_current_user)],
    conn: Annotated[Connection, Depends(get_conn)],
    x_workspace_id: Annotated[str | None, Header(alias="X-Workspace-Id")] = None,
) -> dict[str, Any]:
    workspaces = load_workspaces_visible(conn, user.username, user.roles)
    try:
        active = resolve_effective_workspace_id(conn, user, x_workspace_id)
    except HTTPException:
        active = workspaces[0]["id"] if workspaces else None
    is_admin = False
    permissions: list[str] = []
    if active is not None and user.user_id is not None:
        is_admin, permissions = effective_permissions_for_user(
            conn, user_id=user.user_id, workspace_id=active
        )
    elif active is not None:
        uid = resolve_actor_user_id(conn, user)
        if uid is not None:
            is_admin, permissions = effective_permissions_for_user(
                conn, user_id=uid, workspace_id=active
            )
    return {
        "username": user.username,
        "roles": sorted(user.roles),
        "user_id": user.user_id,
        "workspaces": workspaces,
        "active_workspace_id": active,
        "is_workspace_admin": is_admin,
        "permissions": permissions,
    }


@router.get("/meta/dagster-url")
def meta_dagster(
    _: Annotated[AuthUser, Depends(require_operation("view_ops_console_hint"))],
) -> dict[str, str]:
    return {
        "dagster_ui_url": dagster_console_url(),
        "note": "Операционная консоль оркестрации (Dagster) — технический инструмент для админа и интегратора.",
    }


@router.get("/data/sales-summary")
def data_sales_summary(
    _: Annotated[AuthUser, Depends(require_operation("view_sales_summary"))],
    conn: Annotated[Connection, Depends(get_conn)],
) -> dict[str, Any]:
    t = warehouse_table_sql()
    total = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar_one()
    last = conn.execute(text(f"SELECT MAX(loaded_at) FROM {t}")).scalar()
    return {"table": t, "row_count": int(total), "max_loaded_at": last.isoformat() if last else None}


@router.get("/data/sales-rows")
def data_sales_rows(
    _: Annotated[AuthUser, Depends(require_operation("view_sales_rows"))],
    conn: Annotated[Connection, Depends(get_conn)],
    limit: int = 50,
) -> dict[str, Any]:
    lim = max(1, min(limit, 500))
    t = warehouse_table_sql()
    rows = conn.execute(
        text(
            f"SELECT source_system, source_record_id, event_datetime, amount, amount_rub, "
            f"currency_code, channel, status, loaded_at FROM {t} ORDER BY loaded_at DESC NULLS LAST LIMIT :lim"
        ),
        {"lim": lim},
    ).mappings().all()
    return {"rows": [dict(r) for r in rows]}


@router.get("/data/staging-counts")
def data_staging_counts(
    _: Annotated[AuthUser, Depends(require_operation("view_staging_counts"))],
    conn: Annotated[Connection, Depends(get_conn)],
) -> dict[str, Any]:
    oz = int(conn.execute(text("SELECT COUNT(*) FROM raw_ozon_postings_staging")).scalar_one())
    c1 = int(conn.execute(text("SELECT COUNT(*) FROM raw_1c_orders_staging")).scalar_one())
    sh = int(conn.execute(text("SELECT COUNT(*) FROM raw_google_sheet_orders_staging")).scalar_one())
    return {
        "raw_ozon_postings_staging": oz,
        "raw_1c_orders_staging": c1,
        "raw_google_sheet_orders_staging": sh,
    }


@router.get("/data/destinations-catalog")
def data_destinations_catalog(
    user: Annotated[AuthUser, Depends(require_operation("view_destinations_page"))],
    conn: Annotated[Connection, Depends(get_conn)],
    workspace_code: str = "main",
) -> dict[str, Any]:
    """Каталог приёмников для React SPA: записи ELT destination."""
    n_rows = warehouse_row_count(conn)

    items: list[dict[str, Any]] = []

    wid = resolve_effective_workspace_id(conn, user, None)
    _ = workspace_code
    for drow in list_destinations(conn, workspace_id=wid):
        pl = public_destination_payload(drow)
        cc = str(pl["connector_code"])
        type_labels = {
            "postgres": "PostgreSQL",
            "csv": "CSV",
            "xlsx": "XLSX",
            "clickhouse": "ClickHouse",
        }
        cfg = pl.get("config") or {}
        schema_hint = ""
        if isinstance(cfg, dict):
            if cc.lower() in ("postgres", "postgresql", "warehouse"):
                schema_hint = f"{cfg.get('schema', 'public')}.{cfg.get('table') or cfg.get('table_name', '—')}"
            elif cc.lower() in ("csv",):
                schema_hint = str(cfg.get("path") or "—")
            elif cc.lower() in ("xlsx",):
                schema_hint = str(cfg.get("path") or "—")
            elif cc.lower() in ("clickhouse",):
                schema_hint = f"{cfg.get('database', 'default')}.{cfg.get('table', '—')}"
        n_conn = int(
            conn.execute(
                text("SELECT COUNT(*) FROM connection WHERE destination_id = :did AND workspace_id = :wid"),
                {"did": pl["id"], "wid": wid},
            ).scalar_one()
        )
        last = pl.get("last_checked_at") or pl.get("updated_at")
        last_l = "—"
        if last is not None:
            last_l = last.isoformat() if hasattr(last, "isoformat") else str(last)
        st = str(pl.get("status") or "active")
        items.append(
            {
                "id": str(pl["id"]),
                "name": str(pl["name"]),
                "type": type_labels.get(cc.lower(), cc),
                "connector_code": cc,
                "status": "ok" if st == "active" else "warning",
                "schema_or_db": schema_hint or "—",
                "last_used_label": last_l,
                "connection_count": n_conn,
            }
        )

    return {"items": items, "warehouse_row_count": n_rows}


@router.get("/data/staging-ozon-sample")
def data_staging_ozon(
    _: Annotated[AuthUser, Depends(require_operation("view_staging_ozon_sample"))],
    conn: Annotated[Connection, Depends(get_conn)],
    limit: int = 5,
) -> dict[str, Any]:
    lim = max(1, min(limit, 50))
    rows = conn.execute(
        text(
            "SELECT id, ingest_batch_id, ingested_at, _ingest_extracted_at, _ingest_meta, payload_json "
            "FROM raw_ozon_postings_staging ORDER BY id DESC LIMIT :lim"
        ),
        {"lim": lim},
    ).mappings().all()
    return {"rows": [dict(r) for r in rows]}


@router.get("/data/staging-1c-sample")
def data_staging_1c(
    _: Annotated[AuthUser, Depends(require_operation("view_staging_1c_sample"))],
    conn: Annotated[Connection, Depends(get_conn)],
    limit: int = 5,
) -> dict[str, Any]:
    lim = max(1, min(limit, 50))
    rows = conn.execute(
        text(
            "SELECT id, ingest_batch_id, ingested_at, _ingest_extracted_at, _ingest_meta, row_json "
            "FROM raw_1c_orders_staging ORDER BY id DESC LIMIT :lim"
        ),
        {"lim": lim},
    ).mappings().all()
    return {"rows": [dict(r) for r in rows]}


@router.get("/data/staging-sheet-sample")
def data_staging_sheet(
    _: Annotated[AuthUser, Depends(require_operation("view_staging_sheet_sample"))],
    conn: Annotated[Connection, Depends(get_conn)],
    limit: int = 5,
) -> dict[str, Any]:
    lim = max(1, min(limit, 50))
    rows = conn.execute(
        text(
            "SELECT id, ingest_batch_id, ingested_at, _ingest_extracted_at, _ingest_meta, row_json "
            "FROM raw_google_sheet_orders_staging ORDER BY id DESC LIMIT :lim"
        ),
        {"lim": lim},
    ).mappings().all()
    return {"rows": [dict(r) for r in rows]}


@router.get("/data/sync-state")
def data_sync_state(
    _: Annotated[AuthUser, Depends(require_operation("view_sync_state"))],
    conn: Annotated[Connection, Depends(get_conn)],
    workspace_id: Annotated[int, Depends(require_request_workspace_id)],
) -> dict[str, Any]:
    rows = conn.execute(
        text(
            "SELECT id, integration_code, stream_name, sync_mode, cursor_field, cursor_value, "
            "ingest_state, last_success_at, updated_at FROM sync_state "
            "WHERE workspace_id = :wid "
            "ORDER BY integration_code, stream_name"
        ),
        {"wid": workspace_id},
    ).mappings().all()
    return {"rows": [dict(r) for r in rows]}


@router.get("/data/normalization-issues")
def data_norm_issues(
    _: Annotated[AuthUser, Depends(require_operation("view_normalization_issues"))],
    conn: Annotated[Connection, Depends(get_conn)],
    workspace_id: Annotated[int, Depends(require_request_workspace_id)],
    limit: int = 50,
) -> dict[str, Any]:
    lim = max(1, min(limit, 200))
    rows = list_norm_issues_for_workspace(conn, workspace_id=workspace_id, limit=lim)
    return {"rows": rows}


@router.get("/data/normalization-fix-stats")
def data_normalization_fix_stats(
    _: Annotated[AuthUser, Depends(require_operation("view_normalization_issues"))],
    conn: Annotated[Connection, Depends(get_conn)],
    limit: int = 50,
) -> dict[str, Any]:
    """Агрегаты action/field из typed-слоя (_ingest_meta.changes)."""
    lim = max(1, min(limit, 200))
    t = typed_table_sql()
    sql = text(
        f"SELECT elem->>'action' AS action, elem->>'field' AS field, COUNT(*)::bigint AS cnt "
        f"FROM {t}, "
        f"LATERAL jsonb_array_elements(COALESCE(_ingest_meta->'changes', '[]'::jsonb)) AS elem "
        f"WHERE elem->>'action' IS NOT NULL AND elem->>'action' != '' "
        f"GROUP BY 1, 2 ORDER BY cnt DESC LIMIT :lim"
    )
    rows = conn.execute(sql, {"lim": lim}).mappings().all()
    return {"rows": [dict(r) for r in rows]}


@router.get("/data/mapping-profiles")
def data_mapping_profiles(
    _: Annotated[AuthUser, Depends(require_operation("view_mapping_profiles"))],
    conn: Annotated[Connection, Depends(get_conn)],
    workspace_code: str = "main",
) -> dict[str, Any]:
    workspace_id = resolve_workspace_id(conn, workspace_code=workspace_code)
    return {"rows": list_profiles(conn, workspace_id)}


@router.get("/data/mapping-profiles/{profile_id}/versions")
def data_mapping_profile_versions(
    profile_id: int,
    _: Annotated[AuthUser, Depends(require_operation("view_mapping_profiles"))],
    conn: Annotated[Connection, Depends(get_conn)],
) -> dict[str, Any]:
    return {"rows": list_versions(conn, profile_id)}


class MappingProfileDraftBody(BaseModel):
    workspace_code: str = Field(default="main", min_length=1, max_length=64)
    source_type: str = Field(min_length=1, max_length=64)
    stream_name: str = Field(min_length=1, max_length=128)
    profile_name: str = Field(default="default", min_length=1, max_length=128)
    rules_json: dict[str, Any]
    change_note: str | None = Field(default=None, max_length=512)


class MappingProfilePublishBody(BaseModel):
    profile_id: int
    version_id: int


class MappingProfileRollbackBody(BaseModel):
    profile_id: int
    version_id: int
    note: str | None = Field(default=None, max_length=512)


@router.post("/data/mapping-profiles/draft")
def data_mapping_profiles_draft(
    body: MappingProfileDraftBody,
    request: Request,
    user: Annotated[AuthUser, Depends(require_operation("edit_mapping_profiles"))],
    conn: Annotated[Connection, Depends(get_conn)],
) -> dict[str, Any]:
    try:
        workspace_id = resolve_workspace_id(conn, workspace_code=body.workspace_code.strip())
        row = create_draft_version(
            conn,
            workspace_id=workspace_id,
            source_type=body.source_type.strip(),
            stream_name=body.stream_name.strip(),
            profile_name=body.profile_name.strip(),
            rules_json=body.rules_json,
            created_by=user.username,
            change_note=(body.change_note or "").strip() or None,
        )
    except MappingProfileError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error_code": "mapping_profile_error", "error_message": str(exc)},
        ) from exc
    _audit_api(
        conn,
        request,
        user,
        workspace_id=workspace_id,
        action="mapping_draft_create",
        resource_type="mapping_profile_version",
        resource_id=str(row.get("id")),
        payload={"profile_id": row.get("profile_id"), "version": row.get("version")},
    )
    return {"status": "ok", "item": row}


@router.post("/data/mapping-profiles/publish")
def data_mapping_profiles_publish(
    body: MappingProfilePublishBody,
    request: Request,
    user: Annotated[AuthUser, Depends(require_operation("edit_mapping_profiles"))],
    conn: Annotated[Connection, Depends(get_conn)],
) -> dict[str, Any]:
    try:
        row = publish_version(conn, profile_id=body.profile_id, version_id=body.version_id)
    except MappingProfileError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error_code": "mapping_profile_error", "error_message": str(exc)},
        ) from exc
    wid = _mapping_profile_workspace_id(conn, body.profile_id)
    _audit_api(
        conn,
        request,
        user,
        workspace_id=wid,
        action="mapping_publish",
        resource_type="mapping_profile",
        resource_id=str(body.profile_id),
        payload={"version_id": body.version_id, "published_version_id": row.get("id")},
    )
    return {"status": "ok", "item": row}


@router.post("/data/mapping-profiles/activate")
def data_mapping_profiles_activate(
    body: MappingProfilePublishBody,
    request: Request,
    user: Annotated[AuthUser, Depends(require_operation("edit_mapping_profiles"))],
    conn: Annotated[Connection, Depends(get_conn)],
) -> dict[str, Any]:
    try:
        row = activate_profile_version(
            conn,
            profile_id=body.profile_id,
            version_id=body.version_id,
            updated_by=user.username,
        )
    except MappingProfileError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error_code": "mapping_profile_error", "error_message": str(exc)},
        ) from exc
    wid = row.get("workspace_id")
    wid = int(wid) if wid is not None else _mapping_profile_workspace_id(conn, body.profile_id)
    _audit_api(
        conn,
        request,
        user,
        workspace_id=wid,
        action="mapping_activate",
        resource_type="mapping_profile",
        resource_id=str(body.profile_id),
        payload={"active_version_id": body.version_id},
    )
    return {"status": "ok", "item": row}


@router.post("/data/mapping-profiles/rollback")
def data_mapping_profiles_rollback(
    body: MappingProfileRollbackBody,
    request: Request,
    user: Annotated[AuthUser, Depends(require_operation("edit_mapping_profiles"))],
    conn: Annotated[Connection, Depends(get_conn)],
) -> dict[str, Any]:
    try:
        row = rollback_to_version(
            conn,
            profile_id=body.profile_id,
            version_id=body.version_id,
            updated_by=user.username,
            note=(body.note or "").strip() or None,
        )
    except MappingProfileError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error_code": "mapping_profile_error", "error_message": str(exc)},
        ) from exc
    wid = _mapping_profile_workspace_id(conn, body.profile_id)
    _audit_api(
        conn,
        request,
        user,
        workspace_id=wid,
        action="mapping_rollback",
        resource_type="mapping_profile",
        resource_id=str(body.profile_id),
        payload={"from_version_id": body.version_id, "published_version_id": row.get("id")},
    )
    return {"status": "ok", "item": row}


@router.get("/data/dim-sources")
def data_dim_sources(
    _: Annotated[AuthUser, Depends(require_operation("view_dim_sources"))],
    conn: Annotated[Connection, Depends(get_conn)],
) -> dict[str, Any]:
    rows = conn.execute(text("SELECT code, name, description FROM dim_source_system ORDER BY code")).mappings().all()
    return {"rows": [dict(r) for r in rows]}


@router.get("/data/dim-currencies")
def data_dim_currencies(
    _: Annotated[AuthUser, Depends(require_operation("view_dim_currencies"))],
    conn: Annotated[Connection, Depends(get_conn)],
) -> dict[str, Any]:
    rows = conn.execute(text("SELECT code, name FROM dim_currency ORDER BY code")).mappings().all()
    return {"rows": [dict(r) for r in rows]}


@router.get("/data/pipeline-runs")
def data_pipeline_runs(
    _: Annotated[AuthUser, Depends(require_operation("view_pipeline_runs"))],
    conn: Annotated[Connection, Depends(get_conn)],
    limit: int = 30,
) -> dict[str, Any]:
    lim = max(1, min(limit, 200))
    rows = conn.execute(
        text(
            "SELECT id, dagster_run_id, job_name, status, started_at, finished_at, meta "
            "FROM pipeline_run_summary ORDER BY id DESC LIMIT :lim"
        ),
        {"lim": lim},
    ).mappings().all()
    return {"rows": [dict(r) for r in rows]}


@router.get("/admin/users")
def admin_users(
    _: Annotated[AuthUser, Depends(require_operation("view_admin_users"))],
    conn: Annotated[Connection, Depends(get_conn)],
) -> dict[str, Any]:
    return {"users": list_users_with_roles(conn)}


@router.get("/admin/roles")
def admin_roles(
    _: Annotated[AuthUser, Depends(require_operation("view_admin_roles"))],
    conn: Annotated[Connection, Depends(get_conn)],
) -> dict[str, Any]:
    return {"roles": list_roles(conn)}


@router.get("/admin/integration-config")
def admin_integration_config(
    _: Annotated[AuthUser, Depends(require_operation("view_integration_config"))],
    conn: Annotated[Connection, Depends(get_conn)],
) -> dict[str, Any]:
    rows = conn.execute(
        text("SELECT id, config_key, config_value, is_secret, updated_at FROM integration_config ORDER BY id")
    ).mappings().all()
    out = []
    for r in rows:
        d = dict(r)
        if d.get("is_secret") and d.get("config_value"):
            d["config_value"] = "***"
        out.append(d)
    return {"rows": out}


class ConfigPatch(BaseModel):
    config_key: str = Field(min_length=1, max_length=128)
    config_value: str = ""
    is_secret: bool = False


@router.post("/admin/integration-config")
def admin_integration_config_post(
    body: ConfigPatch,
    request: Request,
    user: Annotated[AuthUser, Depends(require_operation("edit_integration_config"))],
    conn: Annotated[Connection, Depends(get_conn)],
) -> dict[str, Any]:
    conn.execute(
        text(
            "INSERT INTO integration_config (config_key, config_value, is_secret) VALUES (:k, :v, :s) "
            "RETURNING id"
        ),
        {"k": body.config_key, "v": body.config_value, "s": body.is_secret},
    )
    _audit_api(
        conn,
        request,
        user,
        workspace_id=None,
        action="integration_config_update",
        resource_type="integration_config",
        resource_id=body.config_key.strip()[:128],
        payload={"is_secret": body.is_secret},
    )
    return {"status": "ok", "config_key": body.config_key}


@router.get("/data/export-sales-csv")
def export_sales_csv(
    _: Annotated[AuthUser, Depends(require_operation("export_sales_csv"))],
    conn: Annotated[Connection, Depends(get_conn)],
    limit: int = 5000,
) -> dict[str, Any]:
    """Псевдо-экспорт для UI: отдаём строки; клиент собирает CSV (экран «выгрузка»)."""
    lim = max(1, min(limit, 5000))
    t = warehouse_table_sql()
    rows = conn.execute(
        text(
            f"SELECT source_system, source_record_id, event_datetime, amount, amount_rub, currency_code, "
            f"channel, status, loaded_at FROM {t} ORDER BY loaded_at DESC NULLS LAST LIMIT :lim"
        ),
        {"lim": lim},
    ).mappings().all()
    return {"rows": [dict(r) for r in rows], "format": "array_for_client_csv"}


class ConnectionUpsertBody(BaseModel):
    integration_code: str = Field(min_length=1, max_length=64)
    stream_name: str = Field(min_length=1, max_length=128)
    sync_mode: str = Field(default="full_refresh", pattern="^(full_refresh|incremental)$")
    cursor_field: str | None = None


class SyncTriggerBody(BaseModel):
    """connection_id — legacy: id строки sync_state; domain_connection_id — логический connection (Фаза 4)."""

    connection_id: int | None = None
    domain_connection_id: int | None = None
    integration_code: str | None = Field(default=None, max_length=64)
    stream_name: str | None = Field(default=None, max_length=128)
    note: str | None = Field(default=None, max_length=512)


class WorkspaceCreateBody(BaseModel):
    org_code: str = Field(min_length=1, max_length=64)
    org_name: str = Field(min_length=1, max_length=255)
    workspace_code: str = Field(min_length=1, max_length=64)
    workspace_name: str = Field(min_length=1, max_length=255)


class IssueActionBody(BaseModel):
    note: str | None = Field(default=None, max_length=1000)


def _run_stage_from_status(status: str) -> str:
    s = (status or "").lower()
    if s == "queued":
        return "extract"
    if s == "running":
        return "dbt_run"
    if s in ("success", "partial"):
        return "complete"
    if s in ("failed", "cancelled"):
        return "validate"
    return "extract"


@v1.get("/sync-streams")
def v1_sync_streams_list(
    _: Annotated[AuthUser, Depends(require_operation("view_api_v1_catalog"))],
    conn: Annotated[Connection, Depends(get_conn)],
    workspace_id: Annotated[int, Depends(require_request_workspace_id)],
) -> dict[str, Any]:
    """Каталог потоков sync_state (курсоры/кэш); доменные connections — GET /api/v1/connections."""
    rows = conn.execute(
        text(
            "SELECT id, integration_code, stream_name, sync_mode, cursor_field, cursor_value, "
            "last_success_at, updated_at FROM sync_state WHERE workspace_id = :wid "
            "ORDER BY integration_code, stream_name"
        ),
        {"wid": workspace_id},
    ).mappings().all()
    return {"items": [dict(r) for r in rows]}


@v1.get("/layers/raw")
def v1_layers_raw(
    _: Annotated[AuthUser, Depends(require_operation("view_api_v1_catalog"))],
    conn: Annotated[Connection, Depends(get_conn)],
    connection_id: int | None = None,
    stream: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    lim = max(1, min(limit, 500))
    filters = ["table_schema = 'raw'"]
    params: dict[str, Any] = {"lim": lim}
    if stream:
        filters.append("table_name LIKE :stream_like")
        params["stream_like"] = f"%__{stream.strip()}%"
    sql = (
        "SELECT table_schema, table_name FROM information_schema.tables "
        "WHERE " + " AND ".join(filters) + " ORDER BY table_name LIMIT :lim"
    )
    tables = [dict(r) for r in conn.execute(text(sql), params).mappings().all()]
    return {"connection_id": connection_id, "stream": stream, "items": tables}


@v1.get("/layers/normalized")
def v1_layers_normalized(
    _: Annotated[AuthUser, Depends(require_operation("view_api_v1_catalog"))],
    conn: Annotated[Connection, Depends(get_conn)],
    connection_id: int | None = None,
    stream: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    lim = max(1, min(limit, 500))
    filters = ["table_schema = 'normalized'"]
    params: dict[str, Any] = {"lim": lim}
    if stream:
        filters.append("table_name LIKE :stream_like")
        params["stream_like"] = f"%__{stream.strip()}%"
    sql = (
        "SELECT table_schema, table_name FROM information_schema.tables "
        "WHERE " + " AND ".join(filters) + " ORDER BY table_name LIMIT :lim"
    )
    tables = [dict(r) for r in conn.execute(text(sql), params).mappings().all()]
    return {"connection_id": connection_id, "stream": stream, "items": tables}


@v1.get("/dbt/models")
def v1_dbt_models(
    _: Annotated[AuthUser, Depends(require_operation("view_api_v1_catalog"))],
) -> dict[str, Any]:
    source = "sql"
    items: list[dict[str, Any]] | None = None
    manifest_items = _models_from_manifest()
    if manifest_items:
        items = manifest_items
        source = "manifest"
    if items is None:
        items = _models_from_sql_scan()
    return {"items": items, "source": source}


@v1.get("/dbt/models/{model_name}/preview")
def v1_dbt_models_preview(
    model_name: str,
    _: Annotated[AuthUser, Depends(require_operation("view_api_v1_catalog"))],
    conn: Annotated[Connection, Depends(get_conn)],
    schema: str = "semantic",
    limit: int = 20,
) -> dict[str, Any]:
    lim = max(1, min(limit, 200))
    model = _safe_ident(model_name.strip().lower(), "model_name")
    schema_ident = _safe_ident(schema.strip().lower(), "schema")
    try:
        rows = conn.execute(
            text(f'SELECT * FROM "{schema_ident}"."{model}" LIMIT :lim'),
            {"lim": lim},
        ).mappings().all()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "model_preview_failed",
                "model_name": model,
                "schema": schema_ident,
                "message": str(exc),
            },
        ) from exc
    return {"model_name": model, "schema": schema_ident, "rows": [dict(r) for r in rows]}


@v1.post("/sync-streams")
def v1_sync_streams_upsert(
    body: ConnectionUpsertBody,
    request: Request,
    user: Annotated[AuthUser, Depends(require_operation("manage_connections_api"))],
    conn: Annotated[Connection, Depends(get_conn)],
    workspace_id: Annotated[int, Depends(require_request_workspace_id)],
) -> dict[str, Any]:
    cv = '{"cursor": null, "edited_via": "api_v1_connections"}'
    ajs = '{"cursor": null, "rows_emitted": 0, "edited_via": "api_v1_connections"}'
    conn.execute(
        text(
            "INSERT INTO sync_state (workspace_id, integration_code, stream_name, sync_mode, cursor_field, cursor_value, ingest_state, last_success_at, updated_at) "
            "VALUES (:wid, :ic, :sn, :sm, :cf, :cv, CAST(:ajs AS jsonb), NOW(), NOW()) "
            "ON CONFLICT (integration_code, stream_name) DO UPDATE SET "
            "workspace_id = EXCLUDED.workspace_id, sync_mode = EXCLUDED.sync_mode, cursor_field = EXCLUDED.cursor_field, updated_at = NOW()"
        ),
        {
            "wid": workspace_id,
            "ic": body.integration_code.strip(),
            "sn": body.stream_name.strip(),
            "sm": body.sync_mode.strip(),
            "cf": (body.cursor_field or "").strip() or None,
            "cv": cv,
            "ajs": ajs,
        },
    )
    _audit_api(
        conn,
        request,
        user,
        workspace_id=workspace_id,
        action="sync_stream_upsert",
        resource_type="sync_state",
        resource_id=f"{body.integration_code.strip()}:{body.stream_name.strip()}",
        payload={"sync_mode": body.sync_mode},
    )
    return {"status": "ok", "integration_code": body.integration_code, "stream_name": body.stream_name}


@v1.get("/syncs")
def v1_syncs_list(
    _: Annotated[AuthUser, Depends(require_operation("view_api_v1_catalog"))],
    conn: Annotated[Connection, Depends(get_conn)],
    workspace_id: Annotated[int, Depends(require_request_workspace_id)],
    limit: int = 50,
) -> dict[str, Any]:
    rows = refresh_recent_sync_runs(conn, limit=limit, workspace_id=workspace_id)
    return {"items": [attach_load_destination(conn, dict(r)) for r in rows]}


@v1.post("/syncs/trigger", status_code=status.HTTP_202_ACCEPTED)
def v1_sync_trigger(
    body: SyncTriggerBody,
    request: Request,
    user: Annotated[AuthUser, Depends(require_operation("manage_syncs_api"))],
    conn: Annotated[Connection, Depends(get_conn)],
    workspace_id: Annotated[int, Depends(require_request_workspace_id)],
) -> dict[str, Any]:
    try:
        connection_id, domain_cid, integration_code, stream_name = resolve_connection(
            conn,
            domain_connection_id=body.domain_connection_id,
            connection_id=body.connection_id,
            integration_code=(body.integration_code or "").strip() or None,
            stream_name=(body.stream_name or "").strip() or None,
            workspace_id=workspace_id,
        )
    except SyncRunError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "invalid_connection",
                "error_message": str(exc),
            },
        ) from exc

    row = create_sync_run(
        conn,
        connection_id=connection_id,
        domain_connection_id=domain_cid,
        integration_code=integration_code,
        stream_name=stream_name,
        triggered_by=user.username,
        note=body.note,
        workspace_id=workspace_id,
    )
    run_id = int(row["id"])
    if domain_cid is not None:
        try:
            row, summary = run_sync_inline_for_connection(
                conn=conn,
                run_id=run_id,
                workspace_id=workspace_id,
                domain_connection_id=int(domain_cid),
            )
        except Exception as exc:
            row = mark_sync_run_failed(conn, run_id=run_id, message=str(exc))
            _audit_api(
                conn,
                request,
                user,
                workspace_id=workspace_id,
                action="trigger_sync",
                resource_type="sync_run",
                resource_id=str(run_id),
                result="failure",
                payload=build_sync_audit_payload(
                    execution_mode="inline",
                    integration_code=integration_code,
                    stream_name=stream_name,
                    domain_connection_id=domain_cid,
                    error=str(exc),
                ),
            )
            raise HTTPException(
                status_code=502,
                detail={
                    "error_code": "elt_sync_failed",
                    "error_message": str(exc),
                    "run_id": run_id,
                },
            ) from exc
        _audit_api(
            conn,
            request,
            user,
            workspace_id=workspace_id,
            action="trigger_sync",
            resource_type="sync_run",
            resource_id=str(run_id),
            payload=build_sync_audit_payload(
                execution_mode="inline",
                integration_code=integration_code,
                stream_name=stream_name,
                domain_connection_id=domain_cid,
                elt_summary=summary or {},
            ),
        )
        return {
            "status": "accepted",
            "message": "Sync completed",
            "run_id": run_id,
            "sync_run": row,
            "summary": summary or {},
            "execution_mode": "inline",
        }
    try:
        row = launch_sync_run_via_dagster(
            conn=conn,
            run_id=run_id,
            integration_code=integration_code,
            stream_name=stream_name,
            triggered_by=user.username,
        )
    except SyncRunError as exc:
        row = mark_sync_run_failed(conn, run_id=run_id, message=str(exc))
        _audit_api(
            conn,
            request,
            user,
            workspace_id=workspace_id,
            action="trigger_sync",
            resource_type="sync_run",
            resource_id=str(run_id),
            result="failure",
            payload=build_sync_audit_payload(
                execution_mode="dagster",
                integration_code=integration_code,
                stream_name=stream_name,
                domain_connection_id=domain_cid,
                error=str(exc),
            ),
        )
        raise HTTPException(
            status_code=502,
            detail={
                "error_code": "dagster_launch_failed",
                "error_message": str(exc),
                "run_id": run_id,
            },
        ) from exc

    _audit_api(
        conn,
        request,
        user,
        workspace_id=workspace_id,
        action="trigger_sync",
        resource_type="sync_run",
        resource_id=str(run_id),
        payload=build_sync_audit_payload(
            execution_mode="dagster",
            integration_code=integration_code,
            stream_name=stream_name,
            domain_connection_id=domain_cid,
            dagster_run_id=row.get("dagster_run_id"),
        ),
    )
    return {
        "status": "accepted",
        "message": "Sync run accepted and launched",
        "run_id": run_id,
        "sync_run": row,
    }


@v1.get("/syncs/{run_id}")
def v1_sync_get(
    run_id: int,
    _: Annotated[AuthUser, Depends(require_operation("view_api_v1_catalog"))],
    conn: Annotated[Connection, Depends(get_conn)],
    workspace_id: Annotated[int, Depends(require_request_workspace_id)],
) -> dict[str, Any]:
    row = get_sync_run(conn, run_id, workspace_id=workspace_id)
    if row is None:
        raise HTTPException(status_code=404, detail={"error_code": "sync_run_not_found"})
    current = refresh_sync_run_status(conn, row)
    return {"item": attach_load_destination(conn, dict(current))}


@v1.get("/syncs/{run_id}/status")
def v1_sync_status(
    run_id: int,
    _: Annotated[AuthUser, Depends(require_operation("view_api_v1_catalog"))],
    conn: Annotated[Connection, Depends(get_conn)],
    workspace_id: Annotated[int, Depends(require_request_workspace_id)],
) -> dict[str, Any]:
    row = get_sync_run(conn, run_id, workspace_id=workspace_id)
    if row is None:
        raise HTTPException(status_code=404, detail={"error_code": "sync_run_not_found"})
    current = refresh_sync_run_status(conn, row)
    return {
        "run_id": current["id"],
        "status": current["status"],
        "started_at": current.get("started_at"),
        "finished_at": current.get("finished_at"),
        "error_message": current.get("error_message"),
        "dagster_run_id": current.get("dagster_run_id"),
    }


@v1.get("/syncs/{run_id}/logs")
def v1_sync_logs(
    run_id: int,
    _: Annotated[AuthUser, Depends(require_operation("view_api_v1_catalog"))],
    conn: Annotated[Connection, Depends(get_conn)],
    workspace_id: Annotated[int, Depends(require_request_workspace_id)],
) -> dict[str, Any]:
    run = get_sync_run(conn, run_id, workspace_id=workspace_id)
    if run is None:
        raise HTTPException(status_code=404, detail={"error_code": "sync_run_not_found"})
    current = refresh_sync_run_status(conn, run)
    rows = conn.execute(
        text(
            "SELECT id, sync_run_id, stage, level, message, technical_details, record_ref, created_at "
            "FROM sync_run_log WHERE sync_run_id = :rid ORDER BY created_at, id"
        ),
        {"rid": run_id},
    ).mappings().all()
    logs = [dict(r) for r in rows]
    if not logs:
        stage = _run_stage_from_status(str(current.get("status") or "queued"))
        synthetic: list[dict[str, Any]] = [
            {"stage": "extract", "level": "info", "message": "Extract: запуск извлечения данных из источника."},
            {"stage": "staging_raw", "level": "info", "message": "Staging raw: запись в raw.* таблицы."},
            {"stage": "normalize", "level": "info", "message": "Normalize: structural rules -> normalized.*."},
            {"stage": "dbt_run", "level": "info", "message": "dbt_run: запуск dbt моделей -> semantic.*."},
            {"stage": "validate", "level": "info", "message": "Validate: проверки качества и целостности."},
            {"stage": "complete", "level": "info", "message": "Complete: завершение sync run."},
        ]
        logs = []
        for idx, row in enumerate(synthetic, start=1):
            level = row["level"]
            if stage == row["stage"] and current.get("status") == "failed":
                level = "error"
            logs.append(
                {
                    "id": -idx,
                    "sync_run_id": run_id,
                    "stage": row["stage"],
                    "level": level,
                    "message": row["message"],
                    "technical_details": {"synthetic": True, "status": current.get("status")},
                    "record_ref": None,
                    "created_at": current.get("updated_at") or current.get("created_at"),
                }
            )
    return {"items": logs}


@v1.get("/syncs/{run_id}/issues")
def v1_sync_issues(
    run_id: int,
    _: Annotated[AuthUser, Depends(require_operation("view_api_v1_catalog"))],
    conn: Annotated[Connection, Depends(get_conn)],
    workspace_id: Annotated[int, Depends(require_request_workspace_id)],
    limit: int = 200,
) -> dict[str, Any]:
    run = get_sync_run(conn, run_id, workspace_id=workspace_id)
    if run is None:
        raise HTTPException(status_code=404, detail={"error_code": "sync_run_not_found"})
    lim = max(1, min(limit, 500))
    items = list_norm_issues_for_run(conn, sync_run_id=run_id, limit=lim)
    return {"items": items}


@v1.post("/syncs/{run_id}/retry", status_code=status.HTTP_202_ACCEPTED)
def v1_sync_retry(
    run_id: int,
    request: Request,
    user: Annotated[AuthUser, Depends(require_operation("manage_syncs_api"))],
    conn: Annotated[Connection, Depends(get_conn)],
    workspace_id: Annotated[int, Depends(require_request_workspace_id)],
) -> dict[str, Any]:
    old = get_sync_run(conn, run_id, workspace_id=workspace_id)
    if old is None:
        raise HTTPException(status_code=404, detail={"error_code": "sync_run_not_found"})
    row = create_sync_run(
        conn,
        connection_id=old.get("connection_id"),
        domain_connection_id=old.get("domain_connection_id"),
        integration_code=old.get("integration_code"),
        stream_name=old.get("stream_name"),
        triggered_by=user.username,
        note=f"retry_of:{run_id}",
        workspace_id=workspace_id,
    )
    new_id = int(row["id"])
    domain_cid = old.get("domain_connection_id")
    if domain_cid is not None:
        try:
            row, summary = run_sync_inline_for_connection(
                conn=conn,
                run_id=new_id,
                workspace_id=workspace_id,
                domain_connection_id=int(domain_cid),
                extra_meta={"retry_of": run_id},
            )
        except Exception as exc:
            row = mark_sync_run_failed(conn, run_id=new_id, message=str(exc))
            _audit_api(
                conn,
                request,
                user,
                workspace_id=workspace_id,
                action="trigger_sync_retry",
                resource_type="sync_run",
                resource_id=str(new_id),
                result="failure",
                payload=build_sync_audit_payload(
                    execution_mode="inline",
                    retry_of=run_id,
                    error=str(exc),
                ),
            )
            raise HTTPException(
                status_code=502,
                detail={
                    "error_code": "elt_sync_failed",
                    "error_message": str(exc),
                    "run_id": new_id,
                },
            ) from exc
        _audit_api(
            conn,
            request,
            user,
            workspace_id=workspace_id,
            action="trigger_sync_retry",
            resource_type="sync_run",
            resource_id=str(new_id),
            payload=build_sync_audit_payload(
                execution_mode="inline",
                retry_of=run_id,
                elt_summary=summary or {},
            ),
        )
        return {
            "status": "accepted",
            "message": "Sync completed",
            "run_id": new_id,
            "sync_run": row,
            "summary": summary or {},
            "execution_mode": "inline",
        }
    try:
        row = launch_sync_run_via_dagster(
            conn=conn,
            run_id=new_id,
            integration_code=old.get("integration_code"),
            stream_name=old.get("stream_name"),
            triggered_by=user.username,
        )
    except SyncRunError as exc:
        row = mark_sync_run_failed(conn, run_id=new_id, message=str(exc))
        _audit_api(
            conn,
            request,
            user,
            workspace_id=workspace_id,
            action="trigger_sync_retry",
            resource_type="sync_run",
            resource_id=str(new_id),
            result="failure",
            payload=build_sync_audit_payload(
                execution_mode="dagster",
                retry_of=run_id,
                error=str(exc),
            ),
        )
        raise HTTPException(
            status_code=502,
            detail={
                "error_code": "dagster_launch_failed",
                "error_message": str(exc),
                "run_id": new_id,
            },
        ) from exc
    _audit_api(
        conn,
        request,
        user,
        workspace_id=workspace_id,
        action="trigger_sync_retry",
        resource_type="sync_run",
        resource_id=str(new_id),
        payload=build_sync_audit_payload(
            execution_mode="dagster",
            retry_of=run_id,
            dagster_run_id=row.get("dagster_run_id"),
        ),
    )
    return {"status": "accepted", "run_id": new_id, "sync_run": row}


@v1.post("/issues/{issue_id}/resolve")
def v1_issue_resolve(
    issue_id: int,
    body: IssueActionBody,
    request: Request,
    principal: Annotated[WorkspacePrincipal, Depends(require_permission(PERM_CONNECTION_UPDATE))],
    conn: Annotated[Connection, Depends(get_conn)],
    workspace_id: Annotated[int, Depends(require_request_workspace_id)],
) -> dict[str, Any]:
    row = conn.execute(
        text(
            "UPDATE normalization_issue ni SET status = 'resolved', resolved_at = NOW(), "
            "resolved_by = :rb, resolution_note = :note "
            "FROM sync_run sr WHERE ni.id = :id AND ni.sync_run_id = sr.id AND sr.workspace_id = :wid "
            "RETURNING ni.id, COALESCE(ni.status, 'open') AS status, ni.resolved_at, ni.resolved_by, ni.resolution_note"
        ),
        {"id": issue_id, "wid": workspace_id, "rb": principal.user.username, "note": (body.note or "").strip() or None},
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail={"error_code": "issue_not_found"})
    _audit_api(
        conn,
        request,
        principal.user,
        workspace_id=workspace_id,
        action="normalization_issue_resolve",
        resource_type="normalization_issue",
        resource_id=str(issue_id),
        payload={"note": (body.note or "").strip() or None},
    )
    return {"item": dict(row)}


@v1.post("/issues/{issue_id}/ignore")
def v1_issue_ignore(
    issue_id: int,
    body: IssueActionBody,
    request: Request,
    principal: Annotated[WorkspacePrincipal, Depends(require_permission(PERM_CONNECTION_UPDATE))],
    conn: Annotated[Connection, Depends(get_conn)],
    workspace_id: Annotated[int, Depends(require_request_workspace_id)],
) -> dict[str, Any]:
    row = conn.execute(
        text(
            "UPDATE normalization_issue ni SET status = 'ignored', resolved_at = NOW(), "
            "resolved_by = :rb, resolution_note = :note "
            "FROM sync_run sr WHERE ni.id = :id AND ni.sync_run_id = sr.id AND sr.workspace_id = :wid "
            "RETURNING ni.id, COALESCE(ni.status, 'open') AS status, ni.resolved_at, ni.resolved_by, ni.resolution_note"
        ),
        {"id": issue_id, "wid": workspace_id, "rb": principal.user.username, "note": (body.note or "").strip() or None},
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail={"error_code": "issue_not_found"})
    _audit_api(
        conn,
        request,
        principal.user,
        workspace_id=workspace_id,
        action="normalization_issue_ignore",
        resource_type="normalization_issue",
        resource_id=str(issue_id),
        payload={"note": (body.note or "").strip() or None},
    )
    return {"item": dict(row)}


@v1.get("/audit-log")
def v1_audit_log_list(
    _: Annotated[AuthUser, Depends(require_permission(PERM_AUDIT_READ))],
    conn: Annotated[Connection, Depends(get_conn)],
    workspace_id: int | None = None,
    actor: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    result: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    rows = list_audit_log(
        conn,
        workspace_id=workspace_id,
        actor_username=actor,
        action=action,
        resource_type=resource_type,
        result=result,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return {"items": rows}


register_api_v1_catalog_routes(v1)
register_elt_routes(v1)
register_workspace_routes(v1)
register_resource_grant_routes(v1)

router.include_router(v1)
