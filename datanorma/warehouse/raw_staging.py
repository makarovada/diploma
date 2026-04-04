"""Фаза B: персистенция raw в таблицы *_staging и обновление sync_state."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

_log = logging.getLogger(__name__)


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def load_raw_to_staging(
    engine: Engine,
    *,
    raw_ozon: dict[str, Any],
    raw_1c: dict[str, Any],
    raw_sheet: dict[str, Any],
) -> dict[str, Any]:
    batch_id = uuid.uuid4()
    postings = raw_ozon.get("postings") or []
    rows_1c = raw_1c.get("rows") or []
    rows_sheet = raw_sheet.get("rows") or []

    ingest_meta = {
        "batch_id": str(batch_id),
        "ingested_at_utc": datetime.now(timezone.utc).isoformat(),
        "ozon_ingest_mode": raw_ozon.get("ingest_mode"),
        "onec_ingest_mode": raw_1c.get("ingest_mode"),
        "sheet_ingest_mode": raw_sheet.get("ingest_mode"),
    }

    oz_sql = text(
        "INSERT INTO raw_ozon_staging (ingest_batch_id, payload_json) "
        "VALUES (:bid, CAST(:payload AS jsonb))"
    )
    row_sql = text(
        "INSERT INTO raw_1c_staging (ingest_batch_id, row_json) "
        "VALUES (:bid, CAST(:row AS jsonb))"
    )
    sh_sql = text(
        "INSERT INTO raw_sheet_staging (ingest_batch_id, row_json) "
        "VALUES (:bid, CAST(:row AS jsonb))"
    )
    sync_sql = text(
        "INSERT INTO sync_state (integration_code, cursor_value, last_success_at, updated_at) "
        "VALUES (:code, :cur, NOW(), NOW()) "
        "ON CONFLICT (integration_code) DO UPDATE SET "
        "cursor_value = EXCLUDED.cursor_value, "
        "last_success_at = EXCLUDED.last_success_at, "
        "updated_at = NOW()"
    )

    n_oz = n_1c = n_sh = 0
    with engine.begin() as conn:
        for p in postings:
            conn.execute(oz_sql, {"bid": batch_id, "payload": _json_dumps(p)})
            n_oz += 1
        for r in rows_1c:
            conn.execute(row_sql, {"bid": batch_id, "row": _json_dumps(r)})
            n_1c += 1
        for r in rows_sheet:
            conn.execute(sh_sql, {"bid": batch_id, "row": _json_dumps(r)})
            n_sh += 1

        cursor_oz = _json_dumps({**ingest_meta, "table": "raw_ozon_staging", "rows": n_oz})
        cursor_1c = _json_dumps({**ingest_meta, "table": "raw_1c_staging", "rows": n_1c})
        cursor_sh = _json_dumps({**ingest_meta, "table": "raw_sheet_staging", "rows": n_sh})

        conn.execute(sync_sql, {"code": "ozon", "cur": cursor_oz})
        conn.execute(sync_sql, {"code": "1c", "cur": cursor_1c})
        conn.execute(sync_sql, {"code": "google_sheet", "cur": cursor_sh})

    _log.info(
        "staging: batch=%s ozon=%s 1c=%s sheet=%s",
        batch_id,
        n_oz,
        n_1c,
        n_sh,
    )

    return {
        "ingest_batch_id": str(batch_id),
        "ozon_rows_written": n_oz,
        "onec_rows_written": n_1c,
        "sheet_rows_written": n_sh,
        "sync_state_codes": ["ozon", "1c", "google_sheet"],
    }
