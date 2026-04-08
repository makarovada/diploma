"""Идемпотентная загрузка канонических строк в PostgreSQL (UPSERT по источнику + id)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine

from datanorma.config import get_settings
from datanorma.warehouse.tables import canonical_sales_table


def _parse_ts(value: Any):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        s = str(value).strip()
        if not s:
            return None
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _parse_date(value: Any):
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    s = str(value).strip()
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def _row_to_payload(row: dict[str, Any], loaded_at: datetime) -> dict[str, Any] | None:
    ss = row.get("source_system")
    sid = row.get("source_record_id")
    if ss is None or sid is None:
        return None
    ss = str(ss).strip()
    sid = str(sid).strip()
    if not ss or not sid:
        return None
    air_at = _parse_ts(row.get("_airbyte_extracted_at")) or loaded_at
    return {
        "source_system": ss,
        "source_record_id": sid,
        "event_datetime": _parse_ts(row.get("event_datetime")),
        "amount": row.get("amount"),
        "amount_rub": row.get("amount_rub"),
        "currency_code": (str(row["currency_code"]).strip() if row.get("currency_code") else None),
        "counterparty_name": row.get("counterparty_name"),
        "channel": (str(row["channel"]).strip() if row.get("channel") else None),
        "line_description": row.get("line_description"),
        "status": (str(row["status"]).strip() if row.get("status") else None),
        "cbr_rate_date": _parse_date(row.get("cbr_rate_date")),
        "line_unit_normalized": (
            str(row["line_unit_normalized"]).strip() if row.get("line_unit_normalized") else None
        ),
        "normalization_meta": row.get("normalization_meta"),
        "loaded_at": loaded_at,
        "_airbyte_loaded_at": air_at,
    }


def load_canonical_sales_to_postgres(
    engine: Engine,
    rows: list[dict[str, Any]],
    *,
    table_name: str | None = None,
    chunk_size: int = 500,
) -> dict[str, Any]:
    table = canonical_sales_table(table_name)
    loaded_at = datetime.now(timezone.utc)
    payloads: list[dict[str, Any]] = []
    for r in rows:
        p = _row_to_payload(r, loaded_at)
        if p is not None:
            payloads.append(p)

    key_cols = ("source_system", "source_record_id")
    update_cols = [c.name for c in table.columns if c.name not in key_cols]

    auto_ddl = get_settings().warehouse_auto_ddl_enabled()

    with engine.begin() as conn:
        if auto_ddl:
            table.metadata.create_all(conn, tables=[table], checkfirst=True)

        for i in range(0, len(payloads), chunk_size):
            chunk = payloads[i : i + chunk_size]
            if not chunk:
                continue
            stmt = pg_insert(table).values(chunk)
            excluded = stmt.excluded
            set_map = {col: getattr(excluded, col) for col in update_cols}
            incremental_where = or_(
                table.c._airbyte_loaded_at.is_(None),
                excluded._airbyte_loaded_at.is_(None),
                excluded._airbyte_loaded_at >= table.c._airbyte_loaded_at,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=list(key_cols),
                set_=set_map,
                where=incremental_where,
            )
            conn.execute(stmt)

    return {
        "table": table.name,
        "rows_in_normalized": len(rows),
        "rows_upserted": len(payloads),
        "chunks": (len(payloads) + chunk_size - 1) // chunk_size if payloads else 0,
    }


def count_canonical_sales(engine: Engine, table_name: str | None = None) -> int:
    table = canonical_sales_table(table_name)
    with engine.connect() as conn:
        q = select(func.count()).select_from(table)
        return int(conn.execute(q).scalar_one())
