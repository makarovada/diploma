"""REST API: логин, данные, админка — на каждом маршруте проверка операции RBAC."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.engine import Connection

from datanorma.web.config import dagster_console_url
from datanorma.web.deps import AuthUser, get_conn, get_current_user, require_operation
from datanorma.web.jwt_util import create_access_token
from datanorma.web.passwords import verify_password
from datanorma.web.rbac_matrix import matrix_payload
from datanorma.web.sql_util import warehouse_table_sql
from datanorma.web.users_repo import list_roles, list_users_with_roles, load_user_by_username

router = APIRouter(tags=["api"])
v1 = APIRouter(prefix="/v1", tags=["api-v1"])


class LoginBody(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


@router.post("/auth/login")
def auth_login(body: LoginBody, conn: Annotated[Connection, Depends(get_conn)]) -> dict[str, str]:
    user = load_user_by_username(conn, body.username)
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    token = create_access_token(username=user.username, roles=user.roles)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/auth/me")
def auth_me(user: Annotated[AuthUser, Depends(get_current_user)]) -> dict[str, Any]:
    return {"username": user.username, "roles": sorted(user.roles)}


@router.get("/rbac/matrix")
def rbac_matrix(_: Annotated[AuthUser, Depends(require_operation("view_rbac_matrix"))]) -> dict[str, Any]:
    return matrix_payload()


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


@router.get("/data/staging-ozon-sample")
def data_staging_ozon(
    _: Annotated[AuthUser, Depends(require_operation("view_staging_ozon_sample"))],
    conn: Annotated[Connection, Depends(get_conn)],
    limit: int = 5,
) -> dict[str, Any]:
    lim = max(1, min(limit, 50))
    rows = conn.execute(
        text(
            "SELECT id, ingest_batch_id, ingested_at, _airbyte_extracted_at, _airbyte_meta, payload_json "
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
            "SELECT id, ingest_batch_id, ingested_at, _airbyte_extracted_at, _airbyte_meta, row_json "
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
            "SELECT id, ingest_batch_id, ingested_at, _airbyte_extracted_at, _airbyte_meta, row_json "
            "FROM raw_google_sheet_orders_staging ORDER BY id DESC LIMIT :lim"
        ),
        {"lim": lim},
    ).mappings().all()
    return {"rows": [dict(r) for r in rows]}


@router.get("/data/sync-state")
def data_sync_state(
    _: Annotated[AuthUser, Depends(require_operation("view_sync_state"))],
    conn: Annotated[Connection, Depends(get_conn)],
) -> dict[str, Any]:
    rows = conn.execute(
        text(
            "SELECT id, integration_code, stream_name, sync_mode, cursor_field, cursor_value, "
            "airbyte_state, last_success_at, updated_at FROM sync_state "
            "ORDER BY integration_code, stream_name"
        )
    ).mappings().all()
    return {"rows": [dict(r) for r in rows]}


@router.get("/data/normalization-issues")
def data_norm_issues(
    _: Annotated[AuthUser, Depends(require_operation("view_normalization_issues"))],
    conn: Annotated[Connection, Depends(get_conn)],
    limit: int = 50,
) -> dict[str, Any]:
    lim = max(1, min(limit, 200))
    rows = conn.execute(
        text(
            "SELECT id, batch_id, source_system, source_record_id, field_name, issue_type, message, created_at "
            "FROM normalization_issue ORDER BY id DESC LIMIT :lim"
        ),
        {"lim": lim},
    ).mappings().all()
    return {"rows": [dict(r) for r in rows]}


@router.get("/data/mapping-profiles")
def data_mapping_profiles(
    _: Annotated[AuthUser, Depends(require_operation("view_mapping_profiles"))],
    conn: Annotated[Connection, Depends(get_conn)],
) -> dict[str, Any]:
    rows = conn.execute(
        text("SELECT id, name, version, notes, created_at FROM mapping_profile ORDER BY id")
    ).mappings().all()
    return {"rows": [dict(r) for r in rows]}


@router.post("/data/mapping-profiles/stub")
def data_mapping_profiles_stub(
    _: Annotated[AuthUser, Depends(require_operation("edit_mapping_profiles"))],
) -> dict[str, str]:
    return {"status": "accepted", "note": "Заглушка: в прототипе профили задаются YAML и деплоем, не через API."}


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
    _: Annotated[AuthUser, Depends(require_operation("edit_integration_config"))],
    conn: Annotated[Connection, Depends(get_conn)],
) -> dict[str, Any]:
    conn.execute(
        text(
            "INSERT INTO integration_config (config_key, config_value, is_secret) VALUES (:k, :v, :s) "
            "RETURNING id"
        ),
        {"k": body.config_key, "v": body.config_value, "s": body.is_secret},
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
    integration_code: str | None = Field(default=None, max_length=64)
    stream_name: str | None = Field(default=None, max_length=128)
    note: str | None = Field(default=None, max_length=512)


class WorkspaceCreateBody(BaseModel):
    org_code: str = Field(min_length=1, max_length=64)
    org_name: str = Field(min_length=1, max_length=255)
    workspace_code: str = Field(min_length=1, max_length=64)
    workspace_name: str = Field(min_length=1, max_length=255)


@v1.get("/connections")
def v1_connections_list(
    _: Annotated[AuthUser, Depends(require_operation("manage_connections_api"))],
    conn: Annotated[Connection, Depends(get_conn)],
) -> dict[str, Any]:
    rows = conn.execute(
        text(
            "SELECT integration_code, stream_name, sync_mode, cursor_field, cursor_value, "
            "last_success_at, updated_at FROM sync_state ORDER BY integration_code, stream_name"
        )
    ).mappings().all()
    return {"items": [dict(r) for r in rows]}


@v1.post("/connections")
def v1_connections_upsert(
    body: ConnectionUpsertBody,
    _: Annotated[AuthUser, Depends(require_operation("manage_connections_api"))],
    conn: Annotated[Connection, Depends(get_conn)],
) -> dict[str, Any]:
    cv = '{"cursor": null, "edited_via": "api_v1_connections"}'
    ajs = '{"cursor": null, "rows_emitted": 0, "edited_via": "api_v1_connections"}'
    conn.execute(
        text(
            "INSERT INTO sync_state (integration_code, stream_name, sync_mode, cursor_field, cursor_value, airbyte_state, last_success_at, updated_at) "
            "VALUES (:ic, :sn, :sm, :cf, :cv, CAST(:ajs AS jsonb), NOW(), NOW()) "
            "ON CONFLICT (integration_code, stream_name) DO UPDATE SET "
            "sync_mode = EXCLUDED.sync_mode, cursor_field = EXCLUDED.cursor_field, updated_at = NOW()"
        ),
        {
            "ic": body.integration_code.strip(),
            "sn": body.stream_name.strip(),
            "sm": body.sync_mode.strip(),
            "cf": (body.cursor_field or "").strip() or None,
            "cv": cv,
            "ajs": ajs,
        },
    )
    return {"status": "ok", "integration_code": body.integration_code, "stream_name": body.stream_name}


@v1.get("/syncs")
def v1_syncs_list(
    _: Annotated[AuthUser, Depends(require_operation("manage_syncs_api"))],
    conn: Annotated[Connection, Depends(get_conn)],
    limit: int = 50,
) -> dict[str, Any]:
    lim = max(1, min(limit, 500))
    rows = conn.execute(
        text(
            "SELECT id, dagster_run_id, job_name, status, started_at, finished_at, meta "
            "FROM pipeline_run_summary ORDER BY id DESC LIMIT :lim"
        ),
        {"lim": lim},
    ).mappings().all()
    return {"items": [dict(r) for r in rows]}


@v1.post("/syncs/trigger")
def v1_sync_trigger(
    body: SyncTriggerBody,
    _: Annotated[AuthUser, Depends(require_operation("manage_syncs_api"))],
) -> dict[str, Any]:
    # MVP: декларативная точка для внешнего оркестратора/UI; фактический запуск выполняется Dagster UI/CLI.
    return {
        "status": "accepted",
        "note": "Trigger endpoint is declarative in prototype. Use Dagster run launch for execution.",
        "payload": body.model_dump(),
    }


@v1.get("/workspaces")
def v1_workspaces_list(
    _: Annotated[AuthUser, Depends(require_operation("view_workspaces"))],
    conn: Annotated[Connection, Depends(get_conn)],
) -> dict[str, Any]:
    rows = conn.execute(
        text(
            "SELECT o.code AS org_code, o.name AS org_name, w.code AS workspace_code, w.name AS workspace_name "
            "FROM workspace w JOIN organization o ON o.id = w.organization_id "
            "ORDER BY o.code, w.code"
        )
    ).mappings().all()
    return {"items": [dict(r) for r in rows]}


@v1.post("/workspaces")
def v1_workspaces_create(
    body: WorkspaceCreateBody,
    user: Annotated[AuthUser, Depends(require_operation("manage_workspaces"))],
    conn: Annotated[Connection, Depends(get_conn)],
) -> dict[str, Any]:
    org_code = body.org_code.strip()
    ws_code = body.workspace_code.strip()
    conn.execute(
        text(
            "INSERT INTO organization(code, name) VALUES (:c, :n) "
            "ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name"
        ),
        {"c": org_code, "n": body.org_name.strip()},
    )
    conn.execute(
        text(
            "INSERT INTO workspace(organization_id, code, name) "
            "SELECT o.id, :wc, :wn FROM organization o WHERE o.code = :oc "
            "ON CONFLICT ON CONSTRAINT uq_workspace_org_code DO UPDATE SET name = EXCLUDED.name"
        ),
        {"oc": org_code, "wc": ws_code, "wn": body.workspace_name.strip()},
    )
    conn.execute(
        text(
            "INSERT INTO user_workspace(user_id, workspace_id) "
            "SELECT u.id, w.id FROM app_user u "
            "JOIN workspace w ON w.code = :wc "
            "JOIN organization o ON o.id = w.organization_id AND o.code = :oc "
            "WHERE u.username = :un "
            "ON CONFLICT (user_id, workspace_id) DO NOTHING"
        ),
        {"wc": ws_code, "oc": org_code, "un": user.username},
    )
    return {"status": "ok", "org_code": org_code, "workspace_code": ws_code}


router.include_router(v1)
