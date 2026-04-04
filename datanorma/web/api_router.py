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
    oz = int(conn.execute(text("SELECT COUNT(*) FROM raw_ozon_staging")).scalar_one())
    c1 = int(conn.execute(text("SELECT COUNT(*) FROM raw_1c_staging")).scalar_one())
    sh = int(conn.execute(text("SELECT COUNT(*) FROM raw_sheet_staging")).scalar_one())
    return {"raw_ozon_staging": oz, "raw_1c_staging": c1, "raw_sheet_staging": sh}


@router.get("/data/staging-ozon-sample")
def data_staging_ozon(
    _: Annotated[AuthUser, Depends(require_operation("view_staging_ozon_sample"))],
    conn: Annotated[Connection, Depends(get_conn)],
    limit: int = 5,
) -> dict[str, Any]:
    lim = max(1, min(limit, 50))
    rows = conn.execute(
        text(
            "SELECT id, ingest_batch_id, ingested_at, payload_json FROM raw_ozon_staging "
            "ORDER BY id DESC LIMIT :lim"
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
            "SELECT id, ingest_batch_id, ingested_at, row_json FROM raw_1c_staging "
            "ORDER BY id DESC LIMIT :lim"
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
            "SELECT id, ingest_batch_id, ingested_at, row_json FROM raw_sheet_staging "
            "ORDER BY id DESC LIMIT :lim"
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
        text("SELECT id, integration_code, cursor_value, last_success_at, updated_at FROM sync_state ORDER BY id")
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
