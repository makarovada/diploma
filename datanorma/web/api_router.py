"""REST API: логин, данные, админка — на каждом маршруте проверка операции RBAC."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.engine import Connection

from datanorma.web.config import dagster_console_url
from datanorma.web.deps import AuthUser, get_conn, get_current_user, require_operation
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
from datanorma.web.rbac_matrix import matrix_payload
from datanorma.web.sync_runs import (
    SyncRunError,
    create_sync_run,
    get_sync_run,
    launch_dagster_run,
    mark_sync_run_failed,
    mark_sync_run_running,
    refresh_recent_sync_runs,
    refresh_sync_run_status,
    resolve_connection,
)
from datanorma.web.sql_util import typed_table_sql, warehouse_table_sql
from datanorma.web.api_elt import register_elt_routes
from datanorma.web.users_repo import (
    list_roles,
    list_users_with_roles,
    load_user_by_username,
    update_user_password_hash,
)

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
    if is_legacy_sha256_hash(user.password_hash):
        update_user_password_hash(conn, user.id, hash_password(body.password))
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


@router.get("/data/destinations-catalog")
def data_destinations_catalog(
    _: Annotated[AuthUser, Depends(require_operation("view_destinations_page"))],
    conn: Annotated[Connection, Depends(get_conn)],
) -> dict[str, Any]:
    """Каталог приёмников для React SPA (аналог данных на Jinja /app/destinations)."""
    t = warehouse_table_sql()
    n_rows = int(conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar_one())
    sync_n = int(conn.execute(text("SELECT COUNT(*) FROM sync_state")).scalar_one())
    last_u = conn.execute(text("SELECT MAX(updated_at) FROM sync_state")).scalar()
    last_label = "—"
    if last_u is not None:
        last_label = last_u.isoformat() if hasattr(last_u, "isoformat") else str(last_u)

    items: list[dict[str, Any]] = [
        {
            "id": "postgres",
            "name": "PostgreSQL (warehouse)",
            "type": "PostgreSQL",
            "status": "ok",
            "schema_or_db": f"warehouse / {t}",
            "last_used_label": last_label,
            "connection_count": sync_n,
        },
        {
            "id": "csv",
            "name": "CSV file",
            "type": "CSV",
            "status": "ok",
            "schema_or_db": "экспорт /api/data/export-sales-csv",
            "last_used_label": "—",
            "connection_count": 0,
        },
        {
            "id": "xlsx",
            "name": "Excel (.xlsx)",
            "type": "XLSX",
            "status": "ok",
            "schema_or_db": "файл (Jinja /app/warehouse)",
            "last_used_label": "—",
            "connection_count": 0,
        },
        {
            "id": "json",
            "name": "JSON",
            "type": "JSON",
            "status": "ok",
            "schema_or_db": "API-friendly выгрузка",
            "last_used_label": "—",
            "connection_count": 0,
        },
        {
            "id": "xml",
            "name": "XML",
            "type": "XML",
            "status": "ok",
            "schema_or_db": "legacy / EDI",
            "last_used_label": "—",
            "connection_count": 0,
        },
    ]
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
) -> dict[str, Any]:
    rows = conn.execute(
        text(
            "SELECT id, integration_code, stream_name, sync_mode, cursor_field, cursor_value, "
            "ingest_state, last_success_at, updated_at FROM sync_state "
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
    return {"status": "ok", "item": row}


@router.post("/data/mapping-profiles/publish")
def data_mapping_profiles_publish(
    body: MappingProfilePublishBody,
    _: Annotated[AuthUser, Depends(require_operation("edit_mapping_profiles"))],
    conn: Annotated[Connection, Depends(get_conn)],
) -> dict[str, Any]:
    try:
        row = publish_version(conn, profile_id=body.profile_id, version_id=body.version_id)
    except MappingProfileError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error_code": "mapping_profile_error", "error_message": str(exc)},
        ) from exc
    return {"status": "ok", "item": row}


@router.post("/data/mapping-profiles/activate")
def data_mapping_profiles_activate(
    body: MappingProfilePublishBody,
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
    return {"status": "ok", "item": row}


@router.post("/data/mapping-profiles/rollback")
def data_mapping_profiles_rollback(
    body: MappingProfileRollbackBody,
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


@v1.get("/sync-streams")
def v1_sync_streams_list(
    _: Annotated[AuthUser, Depends(require_operation("view_api_v1_catalog"))],
    conn: Annotated[Connection, Depends(get_conn)],
) -> dict[str, Any]:
    """Каталог потоков sync_state (курсоры/кэш); доменные connections — GET /api/v1/connections."""
    rows = conn.execute(
        text(
            "SELECT id, integration_code, stream_name, sync_mode, cursor_field, cursor_value, "
            "last_success_at, updated_at FROM sync_state ORDER BY integration_code, stream_name"
        )
    ).mappings().all()
    return {"items": [dict(r) for r in rows]}


@v1.post("/sync-streams")
def v1_sync_streams_upsert(
    body: ConnectionUpsertBody,
    _: Annotated[AuthUser, Depends(require_operation("manage_connections_api"))],
    conn: Annotated[Connection, Depends(get_conn)],
) -> dict[str, Any]:
    cv = '{"cursor": null, "edited_via": "api_v1_connections"}'
    ajs = '{"cursor": null, "rows_emitted": 0, "edited_via": "api_v1_connections"}'
    conn.execute(
        text(
            "INSERT INTO sync_state (integration_code, stream_name, sync_mode, cursor_field, cursor_value, ingest_state, last_success_at, updated_at) "
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
    _: Annotated[AuthUser, Depends(require_operation("view_api_v1_catalog"))],
    conn: Annotated[Connection, Depends(get_conn)],
    limit: int = 50,
) -> dict[str, Any]:
    return {"items": refresh_recent_sync_runs(conn, limit=limit)}


@v1.post("/syncs/trigger", status_code=status.HTTP_202_ACCEPTED)
def v1_sync_trigger(
    body: SyncTriggerBody,
    user: Annotated[AuthUser, Depends(require_operation("manage_syncs_api"))],
    conn: Annotated[Connection, Depends(get_conn)],
) -> dict[str, Any]:
    try:
        connection_id, domain_cid, integration_code, stream_name = resolve_connection(
            conn,
            domain_connection_id=body.domain_connection_id,
            connection_id=body.connection_id,
            integration_code=(body.integration_code or "").strip() or None,
            stream_name=(body.stream_name or "").strip() or None,
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
    )
    run_id = int(row["id"])
    try:
        launch = launch_dagster_run(
            sync_run_id=run_id,
            integration_code=integration_code,
            stream_name=stream_name,
            triggered_by=user.username,
        )
        row = mark_sync_run_running(conn, run_id=run_id, dagster_run_id=launch.run_id)
    except SyncRunError as exc:
        row = mark_sync_run_failed(conn, run_id=run_id, message=str(exc))
        raise HTTPException(
            status_code=502,
            detail={
                "error_code": "dagster_launch_failed",
                "error_message": str(exc),
                "run_id": run_id,
            },
        ) from exc

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
) -> dict[str, Any]:
    row = get_sync_run(conn, run_id)
    if row is None:
        raise HTTPException(status_code=404, detail={"error_code": "sync_run_not_found"})
    return {"item": refresh_sync_run_status(conn, row)}


@v1.get("/syncs/{run_id}/status")
def v1_sync_status(
    run_id: int,
    _: Annotated[AuthUser, Depends(require_operation("view_api_v1_catalog"))],
    conn: Annotated[Connection, Depends(get_conn)],
) -> dict[str, Any]:
    row = get_sync_run(conn, run_id)
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


register_elt_routes(v1)

router.include_router(v1)
