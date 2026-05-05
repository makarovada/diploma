"""Персистенция raw в таблицы raw_<source>_<stream>_staging и обновление sync_state (Ingest-style)."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from datanorma.ingest.cursor_filter import max_cursor_from_dict_rows, max_cursor_from_postings
from datanorma.ingest.stream_config import parse_all_stream_configs
from datanorma.warehouse.sync_state_repo import build_ingest_state_dict, ensure_phase1_schema

_log = logging.getLogger(__name__)

# Имена таблиц после миграции 002 (whitelist для SQL).
OZ_TABLE = "raw_ozon_postings_staging"
C1_TABLE = "raw_1c_orders_staging"
SH_TABLE = "raw_google_sheet_orders_staging"


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def _oz_sql(table: str) -> Any:
    if table != OZ_TABLE:
        raise ValueError(f"unexpected ozon staging table: {table}")
    return text(
        f"INSERT INTO {OZ_TABLE} (ingest_batch_id, payload_json, _ingest_extracted_at, _ingest_meta) "
        "VALUES (:bid, CAST(:payload AS jsonb), :ext, CAST(:meta AS jsonb))"
    )


def _row_sql(table: str) -> Any:
    if table == C1_TABLE:
        t = C1_TABLE
    elif table == SH_TABLE:
        t = SH_TABLE
    else:
        raise ValueError(f"unexpected tabular staging table: {table}")
    return text(
        f"INSERT INTO {t} (ingest_batch_id, row_json, _ingest_extracted_at, _ingest_meta) "
        "VALUES (:bid, CAST(:row AS jsonb), :ext, CAST(:meta AS jsonb))"
    )


def load_raw_to_staging(
    engine: Engine,
    *,
    raw_ozon: dict[str, Any],
    raw_1c: dict[str, Any],
    raw_sheet: dict[str, Any],
    mappings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_phase1_schema(engine)
    stream_cfgs = parse_all_stream_configs(mappings)
    batch_id = uuid.uuid4()
    extracted_at = datetime.now(timezone.utc)

    postings = raw_ozon.get("postings") or []
    rows_1c = raw_1c.get("rows") or []
    rows_sheet = raw_sheet.get("rows") or []

    oz_cfg = stream_cfgs["ozon"]
    c1_cfg = stream_cfgs["1c"]
    sh_cfg = stream_cfgs["google_sheet"]

    ingest_meta = {
        "batch_id": str(batch_id),
        "ingested_at_utc": extracted_at.isoformat(),
        "ozon_ingest_mode": raw_ozon.get("ingest_mode"),
        "onec_ingest_mode": raw_1c.get("ingest_mode"),
        "sheet_ingest_mode": raw_sheet.get("ingest_mode"),
    }

    oz_table = oz_cfg["table"]
    c1_table = c1_cfg["table"]
    sh_table = sh_cfg["table"]

    oz_sql = _oz_sql(oz_table)
    c1_sql = _row_sql(c1_table)
    sh_sql = _row_sql(sh_table)

    n_oz = n_1c = n_sh = 0
    e_oz = e_1c = e_sh = 0
    with engine.begin() as conn:
        for p in postings:
            try:
                meta = {
                    **ingest_meta,
                    "source": "ozon",
                    "stream": oz_cfg["stream"],
                    "table": oz_table,
                    "record_error": None,
                }
                conn.execute(
                    oz_sql,
                    {
                        "bid": batch_id,
                        "payload": _json_dumps(p),
                        "ext": extracted_at,
                        "meta": _json_dumps(meta),
                    },
                )
                n_oz += 1
            except Exception as exc:
                e_oz += 1
                _log.warning("ozon row skipped: %s", exc)
        for r in rows_1c:
            try:
                meta = {
                    **ingest_meta,
                    "source": "1c",
                    "stream": c1_cfg["stream"],
                    "table": c1_table,
                    "record_error": None,
                }
                conn.execute(
                    c1_sql,
                    {"bid": batch_id, "row": _json_dumps(r), "ext": extracted_at, "meta": _json_dumps(meta)},
                )
                n_1c += 1
            except Exception as exc:
                e_1c += 1
                _log.warning("1c row skipped: %s", exc)
        for r in rows_sheet:
            try:
                meta = {
                    **ingest_meta,
                    "source": "google_sheet",
                    "stream": sh_cfg["stream"],
                    "table": sh_table,
                    "record_error": None,
                }
                conn.execute(
                    sh_sql,
                    {"bid": batch_id, "row": _json_dumps(r), "ext": extracted_at, "meta": _json_dumps(meta)},
                )
                n_sh += 1
            except Exception as exc:
                e_sh += 1
                _log.warning("google_sheet row skipped: %s", exc)

        _persist_stream_state(
            conn,
            integration_code="ozon",
            cfg=oz_cfg,
            rows_emitted=n_oz,
            batch_id=str(batch_id),
            postings=postings,
            tabular_rows=None,
        )
        _persist_stream_state(
            conn,
            integration_code="1c",
            cfg=c1_cfg,
            rows_emitted=n_1c,
            batch_id=str(batch_id),
            postings=None,
            tabular_rows=rows_1c,
        )
        _persist_stream_state(
            conn,
            integration_code="google_sheet",
            cfg=sh_cfg,
            rows_emitted=n_sh,
            batch_id=str(batch_id),
            postings=None,
            tabular_rows=rows_sheet,
        )

    _log.info(
        "staging: batch=%s ozon=%s 1c=%s sheet=%s errors=(%s,%s,%s)",
        batch_id,
        n_oz,
        n_1c,
        n_sh,
        e_oz,
        e_1c,
        e_sh,
    )

    return {
        "ingest_batch_id": str(batch_id),
        "batch_extracted_at": extracted_at.isoformat(),
        "ozon_rows_written": n_oz,
        "onec_rows_written": n_1c,
        "sheet_rows_written": n_sh,
        "row_errors": {"ozon": e_oz, "1c": e_1c, "google_sheet": e_sh},
        "sync_state_codes": ["ozon", "1c", "google_sheet"],
        "staging_tables": {"ozon": oz_table, "1c": c1_table, "google_sheet": sh_table},
    }


def _persist_stream_state(
    conn: Connection,
    integration_code: str,
    cfg: dict[str, Any],
    rows_emitted: int,
    batch_id: str,
    postings: list[dict[str, Any]] | None,
    tabular_rows: list[dict[str, Any]] | None,
) -> None:
    sync_mode = cfg["sync_mode"]
    stream_name = cfg["stream"]
    cursor_field = cfg.get("cursor_field")

    if postings is not None:
        new_cursor = max_cursor_from_postings(postings, cursor_field)
    else:
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
