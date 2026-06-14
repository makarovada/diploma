"""Сиды для демо-окружения: пользователи, workspaces, ELT-подключение, витрина dbt.

Запуск после `alembic upgrade head` и `docker compose up -d`.
Переменная окружения: DATABASE_URL (как в приложении).

Повторный запуск удаляет объекты с префиксом «Seed » / seed_* и пересоздаёт их.
Legacy-таблицы Phase A (raw_*_staging, pipeline_run_summary, …) трогаются только если ещё есть в БД.
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Connection, Engine

from datanorma.config import get_settings
from datanorma.web.elt_repo import ensure_sync_state_for_stream
from datanorma.web.passwords import hash_password

_BATCH = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-000000000001")
_SEED_MARKER = "seed_demo"
_SEED_NAME_PREFIX = "Seed "


def _url() -> str:
    return get_settings().database_url


def _tables(conn: Connection) -> set[str]:
    return set(inspect(conn).get_table_names())


def _columns(conn: Connection, table: str) -> set[str]:
    return {c["name"] for c in inspect(conn).get_columns(table)}


def _has_table(conn: Connection, table: str) -> bool:
    return table in _tables(conn)


def _main_workspace_id(conn: Connection) -> int | None:
    wid = conn.execute(
        text("SELECT id FROM workspace WHERE code = 'main' ORDER BY id LIMIT 1")
    ).scalar()
    if wid is not None:
        return int(wid)
    fallback = conn.execute(text("SELECT id FROM workspace ORDER BY id LIMIT 1")).scalar()
    return int(fallback) if fallback is not None else None


def _delete_if_table(conn: Connection, table: str, where_sql: str, params: dict[str, Any] | None = None) -> None:
    if not _has_table(conn, table):
        return
    conn.execute(text(f"DELETE FROM {table} WHERE {where_sql}"), params or {})


def _clear_seed_rows(conn: Connection) -> None:
    try:
        with conn.begin_nested():
            conn.execute(
                text("DELETE FROM normalized.seed_demo__orders WHERE source_system LIKE 'seed_%'")
            )
    except Exception:
        pass

    if _has_table(conn, "normalization_issue"):
        cols = _columns(conn, "normalization_issue")
        if "error_code" in cols:
            conn.execute(
                text("DELETE FROM normalization_issue WHERE error_code = :m"),
                {"m": _SEED_MARKER},
            )
        elif "issue_type" in cols:
            conn.execute(
                text("DELETE FROM normalization_issue WHERE issue_type = :m"),
                {"m": _SEED_MARKER},
            )

    if _has_table(conn, "sync_run_log") and _has_table(conn, "sync_run"):
        conn.execute(
            text(
                "DELETE FROM sync_run_log WHERE sync_run_id IN "
                "(SELECT id FROM sync_run WHERE dagster_run_id LIKE 'seed-%' OR triggered_by = 'seed_script')"
            )
        )

    _delete_if_table(
        conn,
        "sync_run",
        "dagster_run_id LIKE 'seed-%' OR triggered_by = 'seed_script'",
    )

    if _has_table(conn, "connection_column_rule") and _has_table(conn, "connection_stream_rules"):
        conn.execute(
            text(
                """
                DELETE FROM connection_column_rule
                WHERE stream_rules_id IN (
                  SELECT csr.id
                  FROM connection_stream_rules csr
                  JOIN connection c ON c.id = csr.connection_id
                  WHERE c.name LIKE :pfx
                )
                """
            ),
            {"pfx": f"{_SEED_NAME_PREFIX}%"},
        )

    if _has_table(conn, "connection_stream_rules"):
        conn.execute(
            text(
                """
                DELETE FROM connection_stream_rules
                WHERE connection_id IN (SELECT id FROM connection WHERE name LIKE :pfx)
                """
            ),
            {"pfx": f"{_SEED_NAME_PREFIX}%"},
        )

    if _has_table(conn, "sync_state") and _has_table(conn, "connection_stream"):
        conn.execute(
            text(
                """
                DELETE FROM sync_state
                WHERE connection_stream_id IN (
                  SELECT cs.id
                  FROM connection_stream cs
                  JOIN connection c ON c.id = cs.connection_id
                  WHERE c.name LIKE :pfx
                )
                """
            ),
            {"pfx": f"{_SEED_NAME_PREFIX}%"},
        )

    if _has_table(conn, "connection_stream"):
        conn.execute(
            text(
                "DELETE FROM connection_stream "
                "WHERE connection_id IN (SELECT id FROM connection WHERE name LIKE :pfx)"
            ),
            {"pfx": f"{_SEED_NAME_PREFIX}%"},
        )

    _delete_if_table(conn, "connection", "name LIKE :pfx", {"pfx": f"{_SEED_NAME_PREFIX}%"})
    _delete_if_table(conn, "source", "name LIKE :pfx", {"pfx": f"{_SEED_NAME_PREFIX}%"})
    _delete_if_table(conn, "destination", "name LIKE :pfx", {"pfx": f"{_SEED_NAME_PREFIX}%"})

    conn.execute(
        text("DELETE FROM user_role WHERE user_id IN (SELECT id FROM app_user WHERE username LIKE 'seed_%')")
    )
    conn.execute(text("DELETE FROM app_user WHERE username LIKE 'seed_%'"))

    _delete_if_table(conn, "pipeline_run_summary", "job_name = 'seed_daily_refresh'")
    _delete_if_table(conn, "sync_state", "integration_code LIKE 'seed_%'")
    _delete_if_table(conn, "mapping_profile_legacy", "name LIKE :pfx", {"pfx": f"{_SEED_NAME_PREFIX}%"})
    _delete_if_table(conn, "integration_config", "config_key LIKE 'seed.%'")

    for staging in ("raw_google_sheet_orders_staging",):
        _delete_if_table(conn, staging, "ingest_batch_id = :bid", {"bid": _BATCH})


def seed_reference(conn: Connection) -> None:
    if _has_table(conn, "dim_currency"):
        currencies = [
            ("RUB", "Российский рубль"),
            ("USD", "Доллар США"),
            ("EUR", "Евро"),
            ("CNY", "Юань"),
            ("KZT", "Тенге"),
            ("BYN", "Белорусский рубль"),
            ("GBP", "Фунт стерлингов"),
            ("CHF", "Швейцарский франк"),
        ]
        for code, name in currencies:
            conn.execute(
                text(
                    "INSERT INTO dim_currency (code, name) VALUES (:c, :n) ON CONFLICT (code) DO NOTHING"
                ),
                {"c": code, "n": name},
            )

    if _has_table(conn, "dim_country"):
        for code, name in (("RU", "Россия"), ("KZ", "Казахстан"), ("BY", "Беларусь")):
            conn.execute(
                text("INSERT INTO dim_country (code, name) VALUES (:c, :n) ON CONFLICT (code) DO NOTHING"),
                {"c": code, "n": name},
            )

    if _has_table(conn, "dim_unit"):
        for code, name in (("pcs", "Штуки"), ("kg", "Килограмм"), ("m", "Метр")):
            conn.execute(
                text("INSERT INTO dim_unit (code, name) VALUES (:c, :n) ON CONFLICT (code) DO NOTHING"),
                {"c": code, "n": name},
            )

    if _has_table(conn, "dim_status_map"):
        status_rows = [
            ("order", "google_sheet", "paid", "order_paid"),
            ("order", "google_sheet", "cancelled", "order_cancelled"),
            ("payment", "google_sheet", "ok", "payment_paid"),
        ]
        for dim, src, raw, canon in status_rows:
            conn.execute(
                text(
                    "INSERT INTO dim_status_map (dimension, source_system, raw_status, canonical_code) "
                    "VALUES (:d, :s, :r, :c) ON CONFLICT (dimension, source_system, raw_status) DO NOTHING"
                ),
                {"d": dim, "s": src, "r": raw, "c": canon},
            )


def seed_roles_and_users(conn: Connection) -> None:
    roles = [
        ("platform_admin", "Администратор платформы"),
        ("data_integrator", "Интегратор данных"),
        ("analyst", "Аналитик (read-only в продукте)"),
    ]
    for name, desc in roles:
        conn.execute(
            text(
                "INSERT INTO role (name, description) VALUES (:n, :d) ON CONFLICT (name) DO NOTHING"
            ),
            {"n": name, "d": desc},
        )
    id_by_name: dict[str, int] = {}
    for rid, rname in conn.execute(text("SELECT id, name FROM role")):
        id_by_name[str(rname)] = int(rid)

    users = [
        ("seed_admin", "seed-admin@example.local", ("platform_admin",), hash_password("AdminDemo2026")),
        ("seed_integrator", "seed-integrator@example.local", ("data_integrator",), hash_password("IntegratorDemo2026")),
        ("seed_analyst", "seed-analyst@example.local", ("analyst",), hash_password("AnalystDemo2026")),
        ("seed_analyst2", "seed-analyst2@example.local", ("analyst",), hash_password("AnalystDemo2026")),
        ("seed_ops", "seed-ops@example.local", ("data_integrator", "analyst"), hash_password("IntegratorDemo2026")),
    ]
    for uname, email, rnames, pw_hash in users:
        res = conn.execute(
            text(
                "INSERT INTO app_user (username, password_hash, email) "
                "VALUES (:u, :p, :e) ON CONFLICT (username) DO UPDATE SET "
                "email = EXCLUDED.email, password_hash = EXCLUDED.password_hash "
                "RETURNING id"
            ),
            {"u": uname, "p": pw_hash, "e": email},
        )
        uid = int(res.scalar_one())
        for rn in rnames:
            rid = id_by_name[rn]
            conn.execute(
                text(
                    "INSERT INTO user_role (user_id, role_id) VALUES (:uid, :rid) "
                    "ON CONFLICT DO NOTHING"
                ),
                {"uid": uid, "rid": rid},
            )


def seed_workspace_acl_demo(conn: Connection) -> None:
    """Демо: второе пространство и права участников."""
    admin = conn.execute(text("SELECT id FROM app_user WHERE username = 'seed_admin'")).scalar()
    integrator = conn.execute(text("SELECT id FROM app_user WHERE username = 'seed_integrator'")).scalar()
    analyst = conn.execute(text("SELECT id FROM app_user WHERE username = 'seed_analyst'")).scalar()
    if admin is None:
        return
    conn.execute(
        text(
            "INSERT INTO organization(code, name) VALUES ('ws-demo', 'Demo Org') "
            "ON CONFLICT (code) DO NOTHING"
        )
    )
    conn.execute(
        text(
            """
            INSERT INTO workspace(organization_id, code, name, created_by_user_id)
            SELECT o.id, 'demo', 'Демо-песочница', :uid
            FROM organization o WHERE o.code = 'ws-demo'
            ON CONFLICT ON CONSTRAINT uq_workspace_org_code DO UPDATE SET name = EXCLUDED.name
            """
        ),
        {"uid": int(admin)},
    )
    demo_wid = conn.execute(text("SELECT w.id FROM workspace w WHERE w.code = 'demo'")).scalar()
    if demo_wid is None:
        return
    for uid, adm in ((admin, True), (integrator, False), (analyst, False)):
        if uid is None:
            continue
        conn.execute(
            text(
                "INSERT INTO user_workspace(user_id, workspace_id, is_admin) "
                "VALUES (:u, :w, :a) ON CONFLICT (user_id, workspace_id) "
                "DO UPDATE SET is_admin = EXCLUDED.is_admin"
            ),
            {"u": int(uid), "w": int(demo_wid), "a": adm},
        )
    integrator_perms = [
        "source.create",
        "source.read",
        "source.update",
        "destination.create",
        "destination.read",
        "connection.create",
        "connection.read",
        "connection.sync.run",
        "mapping.read",
        "mapping.edit",
    ]
    analyst_perms = ["source.read", "destination.read", "connection.read", "mapping.read"]
    if integrator:
        for p in integrator_perms:
            conn.execute(
                text(
                    "INSERT INTO workspace_member_permission(workspace_id, user_id, permission_code) "
                    "VALUES (:w, :u, :p) ON CONFLICT DO NOTHING"
                ),
                {"w": int(demo_wid), "u": int(integrator), "p": p},
            )
    if analyst:
        for p in analyst_perms:
            conn.execute(
                text(
                    "INSERT INTO workspace_member_permission(workspace_id, user_id, permission_code) "
                    "VALUES (:w, :u, :p) ON CONFLICT DO NOTHING"
                ),
                {"w": int(demo_wid), "u": int(analyst), "p": p},
            )


def seed_workspace_acl_for_all_existing_workspaces(conn: Connection) -> None:
    """Выдать membership всем пользователям на все workspaces (без 403 в UI)."""
    seed_admin_uid = conn.execute(
        text("SELECT id FROM app_user WHERE username = 'seed_admin'")
    ).scalar()
    if seed_admin_uid is None:
        return

    workspace_ids = conn.execute(text("SELECT id FROM workspace")).scalars().all()
    if not workspace_ids:
        return

    conn.execute(
        text(
            """
            INSERT INTO user_workspace (user_id, workspace_id, is_admin)
            SELECT u.id,
                   w.id,
                   (u.id = :seed_uid) AS is_admin
            FROM app_user u
            CROSS JOIN workspace w
            ON CONFLICT (user_id, workspace_id)
            DO UPDATE SET is_admin = user_workspace.is_admin OR EXCLUDED.is_admin
            """
        ),
        {"seed_uid": int(seed_admin_uid)},
    )

    integrator_perms = [
        "source.create",
        "source.read",
        "source.update",
        "source.delete",
        "destination.create",
        "destination.read",
        "destination.update",
        "destination.delete",
        "connection.create",
        "connection.read",
        "connection.update",
        "connection.delete",
        "connection.sync.run",
        "mapping.read",
        "mapping.edit",
    ]
    analyst_perms = [
        "source.read",
        "destination.read",
        "connection.read",
        "mapping.read",
    ]

    user_role_rows = conn.execute(
        text(
            """
            SELECT ur.user_id, r.name
            FROM user_role ur
            JOIN role r ON r.id = ur.role_id
            """
        )
    ).all()
    roles_by_user: dict[int, set[str]] = {}
    for user_id, role_name in user_role_rows:
        roles_by_user.setdefault(int(user_id), set()).add(str(role_name))

    for wid in workspace_ids:
        for user_id, roles in roles_by_user.items():
            if user_id == int(seed_admin_uid):
                continue
            perm_codes: set[str] = set()
            if "data_integrator" in roles:
                perm_codes.update(integrator_perms)
            if "analyst" in roles:
                perm_codes.update(analyst_perms)
            if not perm_codes:
                continue
            for p in perm_codes:
                conn.execute(
                    text(
                        "INSERT INTO workspace_member_permission (workspace_id, user_id, permission_code) "
                        "VALUES (:w, :u, :p) ON CONFLICT DO NOTHING"
                    ),
                    {"w": int(wid), "u": int(user_id), "p": p},
                )


def _save_seed_stream_rules(
    conn: Connection,
    *,
    connection_id: int,
    stream_name: str,
    sync_mode: str,
    cursor_field: str | None,
    primary_key: list[str],
    columns: list[dict[str, Any]],
) -> None:
    if not _has_table(conn, "connection_stream_rules"):
        return
    stream_rules_id = conn.execute(
        text(
            """
            INSERT INTO connection_stream_rules (
              connection_id, stream_name, sync_mode, cursor_field, primary_key,
              drop_unknown_columns, deduplicate, enabled
            )
            VALUES (
              :cid, :sn, COALESCE(:sm, 'full_refresh'), :cf,
              COALESCE(CAST(:pk AS jsonb), '[]'::jsonb), FALSE, TRUE, TRUE
            )
            ON CONFLICT (connection_id, stream_name) DO UPDATE SET
              sync_mode = EXCLUDED.sync_mode,
              cursor_field = EXCLUDED.cursor_field,
              primary_key = EXCLUDED.primary_key,
              enabled = TRUE,
              updated_at = NOW()
            RETURNING id
            """
        ),
        {
            "cid": connection_id,
            "sn": stream_name,
            "sm": sync_mode,
            "cf": cursor_field,
            "pk": json.dumps(primary_key, ensure_ascii=False),
        },
    ).scalar()
    if stream_rules_id is None or not _has_table(conn, "connection_column_rule"):
        return
    conn.execute(
        text("DELETE FROM connection_column_rule WHERE stream_rules_id = :rid"),
        {"rid": stream_rules_id},
    )
    for idx, col in enumerate(columns):
        conn.execute(
            text(
                """
                INSERT INTO connection_column_rule
                  (stream_rules_id, source_field, target_field, type, nullable, required, params, on_error, sort_order, description)
                VALUES
                  (:rid, :sf, :tf, :tp, TRUE, COALESCE(:req, FALSE), '{}'::jsonb, 'null', :so, NULL)
                """
            ),
            {
                "rid": stream_rules_id,
                "sf": str(col.get("source_field") or ""),
                "tf": str(col.get("target_field") or col.get("source_field") or ""),
                "tp": str(col.get("type") or "string"),
                "req": bool(col.get("required", False)),
                "so": idx,
            },
        )


def _seed_legacy_optional(conn: Connection) -> None:
    """Опциональные сиды для старых таблиц Phase A (если миграции ещё не удалили)."""
    if _has_table(conn, "integration_config"):
        for k, v, sec in (
            ("seed.pipeline.batch_size", "500", False),
            ("seed.pipeline.retry_max", "3", False),
            ("seed.feature.flags", '{"staging_writes": true}', False),
        ):
            conn.execute(
                text(
                    "INSERT INTO integration_config (config_key, config_value, is_secret) "
                    "VALUES (:k, :v, :s)"
                ),
                {"k": k, "v": v, "s": sec},
            )

    if _has_table(conn, "mapping_profile_legacy"):
        for i in range(2):
            conn.execute(
                text(
                    "INSERT INTO mapping_profile_legacy (name, version, notes) VALUES (:n, :ver, :notes)"
                ),
                {
                    "n": f"{_SEED_NAME_PREFIX}profile {i + 1}",
                    "ver": 1,
                    "notes": f"Демо-профиль маппинга #{i + 1}",
                },
            )

    if not _has_table(conn, "sync_state"):
        return
    cols = _columns(conn, "sync_state")
    if "connection_stream_id" in cols:
        return
    syncs = [
        ("seed_sheet", "row:840"),
    ]
    ajs = '{"cursor": null, "rows_emitted": 0, "edited_via": "seed"}'
    for code, cursor in syncs:
        cv = json.dumps({"cursor": cursor, "seed": True}, ensure_ascii=False)
        conn.execute(
            text(
                "INSERT INTO sync_state (integration_code, stream_name, sync_mode, cursor_field, cursor_value, ingest_state, last_success_at, updated_at) "
                "VALUES (:c, 'orders', 'full_refresh', NULL, :cv, CAST(:ajs AS jsonb), NOW(), NOW()) "
                "ON CONFLICT (integration_code, stream_name) DO UPDATE SET cursor_value = EXCLUDED.cursor_value, updated_at = NOW()"
            ),
            {"c": code, "cv": cv, "ajs": ajs},
        )

    for staging, payload_col, payload in (
        ("raw_google_sheet_orders_staging", "row_json", json.dumps({"sheet_row": 1, "client": "Client 1"})),
    ):
        if not _has_table(conn, staging):
            continue
        conn.execute(
            text(
                f"INSERT INTO {staging} (ingest_batch_id, {payload_col}, _ingest_extracted_at, _ingest_meta) "
                "VALUES (:b, CAST(:j AS jsonb), NOW(), CAST(:m AS jsonb))"
            ),
            {"b": _BATCH, "j": payload, "m": json.dumps({"seed": True})},
        )

    if _has_table(conn, "pipeline_run_summary"):
        for i in range(4):
            conn.execute(
                text(
                    "INSERT INTO pipeline_run_summary (dagster_run_id, job_name, status, started_at, finished_at, meta) "
                    "VALUES (:rid, 'seed_daily_refresh', :st, NOW() - INTERVAL '1 hour', NOW(), CAST(:m AS jsonb))"
                ),
                {
                    "rid": f"seed-run-{i:04d}",
                    "st": "success" if i % 2 == 0 else "failed",
                    "m": json.dumps({"rows": 100 + i}),
                },
            )


def seed_elt_demo(conn: Connection) -> dict[str, int | None]:
    """Демо-подключение google_sheet → csv в workspace main (актуальная ELT-модель)."""
    out: dict[str, int | None] = {
        "workspace_id": None,
        "source_id": None,
        "destination_id": None,
        "connection_id": None,
    }
    required = ("source", "destination", "connection", "connection_stream")
    if not all(_has_table(conn, t) for t in required):
        return out

    wid = _main_workspace_id(conn)
    if wid is None:
        return out
    out["workspace_id"] = wid

    integrator_uid = conn.execute(
        text("SELECT id FROM app_user WHERE username = 'seed_integrator'")
    ).scalar()

    repo = get_settings().resolved_repo_root()
    csv_dir = repo / "data" / "seed_output"
    csv_dir.mkdir(parents=True, exist_ok=True)

    src_cfg = json.dumps({}, ensure_ascii=False)
    dst_cfg = json.dumps(
        {"path": str(csv_dir), "filename": "seed_sheets_orders.csv"},
        ensure_ascii=False,
    )

    src_id = conn.execute(
        text(
            """
            INSERT INTO source (workspace_id, name, connector_code, config_encrypted, status, created_by, created_by_user_id, created_at, updated_at)
            VALUES (:wid, :name, 'google_sheet', :cfg, 'active', 'seed_script', :uid, NOW(), NOW())
            RETURNING id
            """
        ),
        {
            "wid": wid,
            "name": f"{_SEED_NAME_PREFIX}Google Sheets (демо)",
            "cfg": src_cfg,
            "uid": int(integrator_uid) if integrator_uid is not None else None,
        },
    ).scalar_one()
    out["source_id"] = int(src_id)

    dst_id = conn.execute(
        text(
            """
            INSERT INTO destination (workspace_id, name, connector_code, config_encrypted, status, created_by, created_by_user_id, created_at, updated_at)
            VALUES (:wid, :name, 'csv', :cfg, 'active', 'seed_script', :uid, NOW(), NOW())
            RETURNING id
            """
        ),
        {
            "wid": wid,
            "name": f"{_SEED_NAME_PREFIX}CSV export",
            "cfg": dst_cfg,
            "uid": int(integrator_uid) if integrator_uid is not None else None,
        },
    ).scalar_one()
    out["destination_id"] = int(dst_id)

    conn_id = conn.execute(
        text(
            """
            INSERT INTO connection (
              workspace_id, name, description, source_id, destination_id,
              status, schedule_cron, timezone, is_active, created_by, created_by_user_id, created_at, updated_at
            )
            VALUES (
              :wid, :name, :descr, :sid, :did,
              'active', '0 6 * * *', 'Europe/Moscow', true, 'seed_script', :uid, NOW(), NOW()
            )
            RETURNING id
            """
        ),
        {
            "wid": wid,
            "name": f"{_SEED_NAME_PREFIX}Sheets → CSV",
            "descr": "Демо: sample google_sheet_export.csv → CSV на диск",
            "sid": int(src_id),
            "did": int(dst_id),
            "uid": int(integrator_uid) if integrator_uid is not None else None,
        },
    ).scalar_one()
    out["connection_id"] = int(conn_id)

    stream_name = "orders"
    sync_mode = "incremental"
    destination_sync_mode = "append_dedup"
    cursor_field = "order_id"
    primary_key = "order_id"

    cs_cols = _columns(conn, "connection_stream")
    cs_insert_cols = [
        "connection_id",
        "stream_name",
        "sync_mode",
        "cursor_field",
        "primary_key",
        "is_enabled",
        "cursor_value",
        "mapping_profile_id",
    ]
    cs_insert_vals = [
        ":cid",
        ":sn",
        ":sm",
        ":cf",
        ":pk",
        "true",
        "NULL",
        "NULL",
    ]
    params: dict[str, Any] = {
        "cid": int(conn_id),
        "sn": stream_name,
        "sm": sync_mode,
        "cf": cursor_field,
        "pk": primary_key,
    }
    if "destination_sync_mode" in cs_cols:
        cs_insert_cols.insert(3, "destination_sync_mode")
        cs_insert_vals.insert(3, ":dsm")
        params["dsm"] = destination_sync_mode

    cs_id = conn.execute(
        text(
            f"INSERT INTO connection_stream ({', '.join(cs_insert_cols)}) "
            f"VALUES ({', '.join(cs_insert_vals)}) RETURNING id"
        ),
        params,
    ).scalar_one()

    if _has_table(conn, "sync_state"):
        ensure_sync_state_for_stream(
            conn,
            integration_code="google_sheet",
            stream_name=stream_name,
            sync_mode=sync_mode,
            cursor_field=cursor_field,
            connection_stream_id=int(cs_id),
            workspace_id=wid,
        )

    column_rules = [
        {"source_field": "order_id", "target_field": "order_id", "type": "string", "required": True},
        {"source_field": "order_date", "target_field": "order_date", "type": "date"},
        {"source_field": "customer_name", "target_field": "customer_name", "type": "string"},
        {"source_field": "amount", "target_field": "amount", "type": "decimal"},
        {"source_field": "currency", "target_field": "currency", "type": "string"},
        {"source_field": "channel", "target_field": "channel", "type": "string"},
    ]
    _save_seed_stream_rules(
        conn,
        connection_id=int(conn_id),
        stream_name=stream_name,
        sync_mode=sync_mode,
        cursor_field=cursor_field,
        columns=column_rules,
        primary_key=[primary_key],
    )

    _seed_demo_sync_runs(conn, workspace_id=wid, connection_id=int(conn_id), stream_name=stream_name)
    return out


def _seed_demo_sync_runs(
    conn: Connection,
    *,
    workspace_id: int,
    connection_id: int,
    stream_name: str,
) -> None:
    if not _has_table(conn, "sync_run"):
        return

    sr_cols = _columns(conn, "sync_run")
    issue_cols = _columns(conn, "normalization_issue") if _has_table(conn, "normalization_issue") else set()
    elt_issues = "sync_run_id" in issue_cols and "error_code" in issue_cols

    runs = [
        ("seed-run-0001", "success"),
        ("seed-run-0002", "failed"),
        ("seed-run-0003", "success"),
    ]
    for rid, status in runs:
        insert_cols = ["status", "triggered_by", "dagster_run_id", "started_at", "finished_at", "meta", "created_at", "updated_at"]
        insert_vals = [
            ":st",
            "'seed_script'",
            ":rid",
            "NOW() - INTERVAL '2 hours'",
            "NOW() - INTERVAL '1 hour'",
            "CAST(:meta AS jsonb)",
            "NOW()",
            "NOW()",
        ]
        params: dict[str, Any] = {
            "st": status,
            "rid": rid,
            "meta": json.dumps({"seed": True, "connection_id": connection_id}, ensure_ascii=False),
        }
        if "workspace_id" in sr_cols:
            insert_cols.insert(0, "workspace_id")
            insert_vals.insert(0, ":wid")
            params["wid"] = workspace_id
        if "domain_connection_id" in sr_cols:
            insert_cols.append("domain_connection_id")
            insert_vals.append(":dcid")
            params["dcid"] = connection_id
        if "integration_code" in sr_cols:
            insert_cols.append("integration_code")
            insert_vals.append("'google_sheet'")
        if "stream_name" in sr_cols:
            insert_cols.append("stream_name")
            insert_vals.append(":sn")
            params["sn"] = stream_name

        run_id = conn.execute(
            text(
                f"INSERT INTO sync_run ({', '.join(insert_cols)}) "
                f"VALUES ({', '.join(insert_vals)}) RETURNING id"
            ),
            params,
        ).scalar_one()

        if not elt_issues or status != "failed":
            continue
        for i in range(3):
            conn.execute(
                text(
                    """
                    INSERT INTO normalization_issue (
                      sync_run_id, connection_id, stream_name, source_record_id,
                      target_field, error_code, error_text, raw_value, status
                    )
                    VALUES (
                      :sr, :cid, :sn, :sid, :tf, :ec, :et, CAST(:rv AS jsonb), 'open'
                    )
                    """
                ),
                {
                    "sr": int(run_id),
                    "cid": connection_id,
                    "sn": stream_name,
                    "sid": f"GS-50{i + 1}",
                    "tf": "amount",
                    "ec": _SEED_MARKER,
                    "et": f"Демо-ошибка нормализации #{i + 1}",
                    "rv": json.dumps({"amount": "not-a-number"}, ensure_ascii=False),
                },
            )


def seed_normalized_bulk(conn: Connection) -> None:
    """Витрина для dbt source normalized.seed_demo__orders."""
    loaded_at = datetime.now(timezone.utc)
    systems = ["seed_sheet"]
    conn.execute(text("CREATE SCHEMA IF NOT EXISTS normalized"))
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS normalized.seed_demo__orders (
                id bigserial PRIMARY KEY,
                source_system text,
                source_record_id text,
                event_datetime timestamptz,
                amount numeric,
                currency_code text,
                status text,
                channel text,
                loaded_at timestamptz
            )
            """
        )
    )
    stmt = text(
        "INSERT INTO normalized.seed_demo__orders ("
        "source_system, source_record_id, event_datetime, amount, currency_code, status, channel, loaded_at"
        ") VALUES ("
        ":ss, :sid, :ed, :am, :cc, :st, :ch, :la)"
    )
    base_date = date(2024, 6, 1)
    for i in range(520):
        ss = systems[i % 3]
        sid = f"{ss.upper()}-{i:05d}"
        d = base_date + timedelta(days=i % 120)
        conn.execute(
            stmt,
            {
                "ss": ss,
                "sid": sid,
                "ed": datetime(d.year, d.month, d.day, 12, 0, tzinfo=timezone.utc),
                "am": Decimal("100.00") + Decimal(i % 50),
                "cc": "RUB",
                "ch": "retail" if i % 2 == 0 else "online",
                "st": "paid",
                "la": loaded_at,
            },
        )


def run(engine: Engine | None = None) -> dict[str, Any]:
    eng = engine or create_engine(_url(), pool_pre_ping=True)
    counts: dict[str, Any] = {}
    with eng.begin() as conn:
        _clear_seed_rows(conn)
        seed_reference(conn)
        seed_roles_and_users(conn)
        seed_workspace_acl_demo(conn)
        seed_workspace_acl_for_all_existing_workspaces(conn)
        _seed_legacy_optional(conn)
        counts["elt_demo"] = seed_elt_demo(conn)
        seed_normalized_bulk(conn)
        counts["normalized_orders_seed"] = conn.execute(
            text("SELECT COUNT(*) FROM normalized.seed_demo__orders WHERE source_system LIKE 'seed_%'")
        ).scalar_one()
        if _has_table(conn, "normalization_issue"):
            ni_cols = _columns(conn, "normalization_issue")
            if "error_code" in ni_cols:
                counts["normalization_issue_seed"] = conn.execute(
                    text("SELECT COUNT(*) FROM normalization_issue WHERE error_code = :m"),
                    {"m": _SEED_MARKER},
                ).scalar_one()
            elif "issue_type" in ni_cols:
                counts["normalization_issue_seed"] = conn.execute(
                    text("SELECT COUNT(*) FROM normalization_issue WHERE issue_type = :m"),
                    {"m": _SEED_MARKER},
                ).scalar_one()
    return counts


def main() -> None:
    c = run()
    print("Seed OK:", c)


if __name__ == "__main__":
    main()
