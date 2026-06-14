"""Чтение и запись sync_state (Ingest-style stream state)."""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine, RowMapping

from datanorma.ingest.dagster_streams import dagster_staging_table_names

_log = logging.getLogger(__name__)


class Phase1SchemaRequiredError(RuntimeError):
    """БД без миграции 002 (Ingest staging / sync_state по потокам)."""


def ensure_phase1_schema(engine: Engine) -> None:
    """Проверка перед sync_catalog / staging: ревизия `002_phase1_ingest` должна быть применена."""
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    if "sync_state" not in tables:
        raise Phase1SchemaRequiredError(
            "В БД нет таблицы sync_state. Выполните: alembic upgrade head "
            "(из корня репозитория, с тем же DATABASE_URL, что у Dagster)."
        )
    sc_cols = {c["name"] for c in insp.get_columns("sync_state")}
    if "stream_name" not in sc_cols:
        raise Phase1SchemaRequiredError(
            "В sync_state нет колонки stream_name — не применена миграция Phase 1. "
            "Выполните из каталога проекта: alembic upgrade head\n"
            "Должна подтянуться ревизия 002_phase1_ingest. "
            "Проверьте, что переменная DATABASE_URL в окружении Dagster совпадает с той, "
            "куда вы накатывали Alembic (например порт Docker 5433, а не локальный 5432)."
        )
    if "raw_google_sheet_orders_staging" not in tables:
        known = dagster_staging_table_names()
        if not any(name in tables for name in known):
            raise Phase1SchemaRequiredError(
                "Нет таблиц raw_*_staging. Примените: alembic upgrade head "
                "(миграция добавляет raw_*_staging и _ingest_* колонки) "
                "или запустите Dagster staging asset (создаёт недостающие таблицы)."
            )


def extract_stream_cursor(row: RowMapping | dict[str, Any] | None) -> str | None:
    """Достаёт строковый курсор из ingest_state или legacy cursor_value JSON."""
    if row is None:
        return None
    air = row.get("ingest_state")
    if isinstance(air, dict):
        st = air.get("stream")
        if isinstance(st, dict) and st.get("cursor") is not None:
            return str(st["cursor"]).strip()
    legacy = row.get("cursor_value")
    if not legacy or not str(legacy).strip():
        return None
    try:
        j = json.loads(str(legacy))
        if isinstance(j, dict):
            c = j.get("cursor") or j.get("stream_cursor")
            if c is not None:
                return str(c).strip()
    except (json.JSONDecodeError, TypeError):
        pass
    return None


def fetch_sync_state_map(engine: Engine) -> dict[tuple[str, str], dict[str, Any]]:
    """Ключ (integration_code, stream_name)."""
    ensure_phase1_schema(engine)
    sql = text(
        "SELECT integration_code, stream_name, sync_mode, cursor_field, cursor_value, "
        "ingest_state, last_success_at, updated_at, connection_stream_id "
        "FROM sync_state "
        "ORDER BY (connection_stream_id IS NULL) DESC, id"
    )
    out: dict[tuple[str, str], dict[str, Any]] = {}
    with engine.connect() as conn:
        for row in conn.execute(sql).mappings().all():
            key = (str(row["integration_code"]), str(row["stream_name"]))
            if key in out:
                continue
            out[key] = dict(row)
    return out


def build_ingest_state_dict(*, cursor: str | None, rows_emitted: int, batch_id: str) -> dict[str, Any]:
    st: dict[str, Any] = {"version": 1, "records_emitted": rows_emitted, "batch_id": batch_id}
    if cursor is not None:
        st["stream"] = {"cursor": cursor}
    return st


def upsert_stream_state(
    engine: Engine,
    *,
    integration_code: str,
    stream_name: str,
    sync_mode: str,
    cursor_field: str | None,
    cursor_value_text: str | None,
    ingest_state: dict[str, Any],
) -> None:
    sql = text(
        "INSERT INTO sync_state (integration_code, stream_name, sync_mode, cursor_field, "
        "cursor_value, ingest_state, last_success_at, updated_at) "
        "VALUES (:ic, :sn, :sm, :cf, :cv, CAST(:ajs AS jsonb), NOW(), NOW()) "
        "ON CONFLICT (integration_code, stream_name) DO UPDATE SET "
        "sync_mode = EXCLUDED.sync_mode, "
        "cursor_field = EXCLUDED.cursor_field, "
        "cursor_value = EXCLUDED.cursor_value, "
        "ingest_state = EXCLUDED.ingest_state, "
        "last_success_at = NOW(), "
        "updated_at = NOW()"
    )
    payload = {
        "ic": integration_code,
        "sn": stream_name,
        "sm": sync_mode,
        "cf": cursor_field,
        "cv": cursor_value_text,
        "ajs": json.dumps(ingest_state, ensure_ascii=False, default=str),
    }
    with engine.begin() as conn:
        conn.execute(sql, payload)
    _log.info("sync_state upsert %s/%s mode=%s cursor=%s", integration_code, stream_name, sync_mode, cursor_field)
