"""Персистенция raw в таблицы raw_<source>_<stream>_staging и обновление sync_state (Ingest-style)."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection, Engine

from datanorma.ingest.cursor_filter import max_cursor_from_dict_rows
from datanorma.ingest.stream_config import parse_all_stream_configs, staging_table_physical_name
from datanorma.warehouse.sync_state_repo import build_ingest_state_dict, ensure_phase1_schema

_log = logging.getLogger(__name__)


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def _row_sql(table: str) -> Any:
    return text(
        f"INSERT INTO {table} (ingest_batch_id, row_json, _ingest_extracted_at, _ingest_meta) "
        "VALUES (:bid, CAST(:row AS jsonb), :ext, CAST(:meta AS jsonb))"
    )


def ensure_raw_staging_table(engine: Engine, table_name: str) -> None:
    """Создаёт raw_*_staging при отсутствии (тот же контракт, что в миграциях Phase 1)."""
    insp = inspect(engine)
    if table_name in insp.get_table_names():
        return
    ddl = text(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id BIGSERIAL PRIMARY KEY,
            ingest_batch_id UUID NOT NULL,
            row_json JSONB NOT NULL,
            ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            _ingest_raw_id UUID NOT NULL DEFAULT gen_random_uuid(),
            _ingest_extracted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            _ingest_meta JSONB NOT NULL DEFAULT '{{}}'::jsonb
        )
        """
    )
    with engine.begin() as conn:
        conn.execute(ddl)
    _log.info("created raw staging table %s", table_name)


def _persist_one_raw_payload(
    conn: Connection,
    *,
    raw_payload: dict[str, Any],
    stream_cfg: dict[str, Any],
    batch_id: uuid.UUID,
    extracted_at: datetime,
) -> tuple[int, int, str]:
    integration_code = str(raw_payload.get("source_system") or stream_cfg.get("yaml_key") or "")
    stream_name = str(raw_payload.get("stream_name") or stream_cfg.get("stream") or "default")
    table_name = str(stream_cfg.get("table") or staging_table_physical_name(integration_code, stream_name))
    rows = raw_payload.get("rows") or []

    ingest_meta = {
        "batch_id": str(batch_id),
        "ingested_at_utc": extracted_at.isoformat(),
        "ingest_mode": raw_payload.get("ingest_mode"),
        "source_ref": raw_payload.get("source_ref"),
    }

    row_sql = _row_sql(table_name)
    written = 0
    errors = 0
    for row in rows:
        try:
            meta = {
                **ingest_meta,
                "source": integration_code,
                "stream": stream_name,
                "table": table_name,
                "record_error": None,
            }
            conn.execute(
                row_sql,
                {"bid": batch_id, "row": _json_dumps(row), "ext": extracted_at, "meta": _json_dumps(meta)},
            )
            written += 1
        except Exception as exc:
            errors += 1
            _log.warning("%s row skipped: %s", integration_code, exc)

    _persist_stream_state(
        conn,
        integration_code=integration_code,
        cfg=stream_cfg,
        rows_emitted=written,
        batch_id=str(batch_id),
        tabular_rows=rows,
    )
    return written, errors, table_name


def load_raw_to_staging(
    engine: Engine,
    *,
    raw_payloads: list[dict[str, Any]] | None = None,
    raw_sheet: dict[str, Any] | None = None,
    mappings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Записывает один или несколько унифицированных raw payload в staging и sync_state."""
    ensure_phase1_schema(engine)
    stream_cfgs = parse_all_stream_configs(mappings)

    payloads = list(raw_payloads or [])
    if raw_sheet is not None:
        legacy = dict(raw_sheet)
        legacy.setdefault("source_system", "google_sheet")
        legacy.setdefault("stream_name", stream_cfgs["google_sheet"]["stream"])
        payloads.append(legacy)

    if not payloads:
        raise ValueError("load_raw_to_staging: нужен хотя бы один raw payload")

    for cfg in stream_cfgs.values():
        ensure_raw_staging_table(engine, str(cfg["table"]))

    batch_id = uuid.uuid4()
    extracted_at = datetime.now(timezone.utc)

    rows_written: dict[str, int] = {}
    row_errors: dict[str, int] = {}
    staging_tables: dict[str, str] = {}
    sync_state_codes: list[str] = []

    with engine.begin() as conn:
        for raw_payload in payloads:
            code = str(raw_payload.get("source_system") or "")
            if code not in stream_cfgs:
                raise ValueError(f"unknown source_system in raw payload: {code!r}")
            cfg = stream_cfgs[code]
            n_written, n_errors, table_name = _persist_one_raw_payload(
                conn,
                raw_payload=raw_payload,
                stream_cfg=cfg,
                batch_id=batch_id,
                extracted_at=extracted_at,
            )
            rows_written[code] = n_written
            row_errors[code] = n_errors
            staging_tables[code] = table_name
            if code not in sync_state_codes:
                sync_state_codes.append(code)

    total_written = sum(rows_written.values())
    _log.info("staging: batch=%s rows=%s errors=%s", batch_id, rows_written, row_errors)

    return {
        "ingest_batch_id": str(batch_id),
        "batch_extracted_at": extracted_at.isoformat(),
        "rows_written": rows_written,
        "sheet_rows_written": total_written,
        "row_errors": row_errors,
        "sync_state_codes": sync_state_codes,
        "staging_tables": staging_tables,
    }


def _persist_stream_state(
    conn: Connection,
    integration_code: str,
    cfg: dict[str, Any],
    rows_emitted: int,
    batch_id: str,
    tabular_rows: list[dict[str, Any]] | None,
) -> None:
    sync_mode = cfg["sync_mode"]
    stream_name = cfg["stream"]
    cursor_field = cfg.get("cursor_field")
    new_cursor = max_cursor_from_dict_rows(tabular_rows or [], cursor_field)

    ingest_state = build_ingest_state_dict(cursor=new_cursor, rows_emitted=rows_emitted, batch_id=batch_id)
    legacy_cv = _json_dumps({"cursor": new_cursor, "batch_id": batch_id, "rows": rows_emitted})

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
        "cv": legacy_cv,
        "ajs": _json_dumps(ingest_state),
    }
    conn.execute(sql, payload)
