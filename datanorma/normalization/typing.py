"""Typing & deduping for canonical rows + typed table upsert."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import Column, Date, DateTime, MetaData, Numeric, PrimaryKeyConstraint, String, Table, Text, func, or_, select
from sqlalchemy.dialects.postgresql import JSONB, insert as pg_insert
from sqlalchemy.engine import Engine

from datanorma.config import get_settings

_META = MetaData()


def load_canonical_schema(path: Path | None = None) -> dict[str, Any]:
    schema_path = path or (Path(__file__).resolve().parent.parent / "schemas" / "canonical_sales.yaml")
    with schema_path.open(encoding="utf-8") as f:
        payload = yaml.safe_load(f) or {}
    if not isinstance(payload.get("fields"), dict):
        raise ValueError(f"Invalid canonical schema: {schema_path}")
    return payload


def _to_datetime(value: Any) -> datetime | None:
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
        dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _to_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    s = str(value).strip()
    if not s:
        return None
    return date.fromisoformat(s[:10])


def _cast_value(field: str, spec: dict[str, Any], raw: Any) -> tuple[Any, dict[str, Any] | None]:
    if raw is None or raw == "":
        return None, None

    type_name = str(spec.get("type") or "string")
    fmt = str(spec.get("format") or "")
    try:
        if field == "event_datetime" or (type_name == "string" and fmt in ("iso8601", "datetime")):
            dt = _to_datetime(raw)
            return dt, {"field": field, "action": "datetime_cast", "from": raw, "to": dt.isoformat() if dt else None}
        if field == "cbr_rate_date" or (type_name == "string" and fmt == "date"):
            d = _to_date(raw)
            return d, {"field": field, "action": "date_cast", "from": raw, "to": d.isoformat() if d else None}
        if type_name == "number":
            if isinstance(raw, (int, float, Decimal)):
                return Decimal(str(raw)), None
            out = Decimal(str(raw).strip().replace(" ", "").replace(",", "."))
            return out, {"field": field, "action": "number_cast", "from": raw, "to": str(out)}
        if type_name == "integer":
            out = int(str(raw).strip())
            return out, {"field": field, "action": "int_cast", "from": raw, "to": out}
        if type_name == "boolean":
            s = str(raw).strip().lower()
            if s in ("1", "true", "yes", "y", "да"):
                return True, {"field": field, "action": "bool_cast", "from": raw, "to": True}
            if s in ("0", "false", "no", "n", "нет"):
                return False, {"field": field, "action": "bool_cast", "from": raw, "to": False}
            raise ValueError(f"unsupported bool literal: {raw!r}")

        out = str(raw).strip()
        return out, ({"field": field, "action": "strip", "from": raw, "to": out} if out != raw else None)
    except (ValueError, TypeError, InvalidOperation) as exc:
        return None, {"field": field, "action": "cast_error", "from": raw, "to": None, "error": str(exc)}


def cast_rows_to_typed(rows: list[dict[str, Any]], canonical_schema: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    fields: dict[str, dict[str, Any]] = canonical_schema.get("fields") or {}
    dedup_keys: set[tuple[str, str]] = set()
    typed_rows: list[dict[str, Any]] = []
    stats = {
        "rows_in": len(rows),
        "rows_out": 0,
        "duplicates_dropped": 0,
        "changes_total": 0,
        "cast_errors": 0,
    }

    for row in rows:
        source_system = str(row.get("source_system") or "").strip()
        source_record_id = str(row.get("source_record_id") or "").strip()
        if source_system and source_record_id:
            key = (source_system, source_record_id)
            if key in dedup_keys:
                stats["duplicates_dropped"] += 1
                continue
            dedup_keys.add(key)

        changes: list[dict[str, Any]] = []
        typed: dict[str, Any] = {}
        for field_name, spec in fields.items():
            casted, change = _cast_value(field_name, spec, row.get(field_name))
            typed[field_name] = casted
            if change is not None:
                changes.append(change)
                stats["changes_total"] += 1
                if change.get("action") == "cast_error":
                    stats["cast_errors"] += 1

        typed["_airbyte_extracted_at"] = _to_datetime(row.get("_airbyte_extracted_at"))
        typed["_airbyte_meta"] = {"changes": changes}
        typed_rows.append(typed)

    stats["rows_out"] = len(typed_rows)
    return typed_rows, stats


def typed_canonical_table(name: str | None = None) -> Table:
    tname = name or get_settings().datanorma_typed_table.strip() or "typed_canonical_sales"
    if tname in _META.tables:
        return _META.tables[tname]
    return Table(
        tname,
        _META,
        Column("source_system", String(64), nullable=False),
        Column("source_record_id", String(512), nullable=False),
        Column("event_datetime", DateTime(timezone=True)),
        Column("amount", Numeric(18, 4)),
        Column("amount_rub", Numeric(18, 4)),
        Column("currency_code", String(16)),
        Column("counterparty_name", Text),
        Column("channel", String(128)),
        Column("line_description", Text),
        Column("status", String(128)),
        Column("line_unit_normalized", String(64)),
        Column("cbr_rate_date", Date),
        Column("_airbyte_extracted_at", DateTime(timezone=True), nullable=True),
        Column("_airbyte_meta", JSONB, nullable=False),
        Column("loaded_at", DateTime(timezone=True), nullable=False),
        PrimaryKeyConstraint("source_system", "source_record_id"),
    )


def upsert_typed_rows(engine: Engine, rows: list[dict[str, Any]], *, table_name: str | None = None, chunk_size: int = 500) -> dict[str, Any]:
    table = typed_canonical_table(table_name)
    loaded_at = datetime.now(timezone.utc)
    payloads = [{**r, "loaded_at": loaded_at} for r in rows]
    key_cols = ("source_system", "source_record_id")
    update_cols = [c.name for c in table.columns if c.name not in key_cols]
    with engine.begin() as conn:
        table.metadata.create_all(conn, tables=[table], checkfirst=True)
        for i in range(0, len(payloads), chunk_size):
            chunk = payloads[i : i + chunk_size]
            if not chunk:
                continue
            stmt = pg_insert(table).values(chunk)
            excluded = stmt.excluded
            stmt = stmt.on_conflict_do_update(
                index_elements=list(key_cols),
                set_={col: getattr(excluded, col) for col in update_cols},
                where=or_(
                    table.c._airbyte_extracted_at.is_(None),
                    excluded._airbyte_extracted_at.is_(None),
                    excluded._airbyte_extracted_at >= table.c._airbyte_extracted_at,
                ),
            )
            conn.execute(stmt)
    return {"table": table.name, "rows_upserted": len(payloads)}


def count_typed_rows(engine: Engine, table_name: str | None = None) -> int:
    table = typed_canonical_table(table_name)
    with engine.connect() as conn:
        return int(conn.execute(select(func.count()).select_from(table)).scalar_one())
