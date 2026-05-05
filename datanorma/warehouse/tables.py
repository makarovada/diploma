"""Определение таблиц normalized-слоя в PostgreSQL."""

from __future__ import annotations

import re

from sqlalchemy import BIGINT, Column, Date, DateTime, MetaData, Numeric, PrimaryKeyConstraint, String, Table, Text, text
from sqlalchemy.dialects.postgresql import JSONB

from datanorma.normalization.rules import StreamRules

metadata = MetaData()


def _safe_ident(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]+", "_", name.strip().lower())
    cleaned = cleaned.strip("_")
    return cleaned or "unknown"


def ensure_normalized_table(
    *,
    connector_code: str,
    stream_rules: StreamRules,
    schema: str = "normalized",
    keep_raw_payload: bool = True,
) -> Table:
    """Создаёт/возвращает таблицу normalized.<connector>__<stream>."""
    table_name = f"{_safe_ident(connector_code)}__{_safe_ident(stream_rules.stream_name)}"
    key = f"{schema}.{table_name}"
    if key in metadata.tables:
        return metadata.tables[key]
    columns: list[Column] = []
    for col in stream_rules.columns:
        if col.type == "string":
            dtype = Text
        elif col.type == "integer":
            dtype = BIGINT
        elif col.type in ("number", "currency_amount"):
            dtype = Numeric(38, 9)
        elif col.type == "currency_code":
            dtype = String(8)
        elif col.type == "boolean":
            from sqlalchemy import Boolean

            dtype = Boolean
        elif col.type == "date":
            dtype = Date
        elif col.type == "datetime":
            dtype = DateTime(timezone=True)
        elif col.type == "phone":
            dtype = String(32)
        elif col.type == "email":
            dtype = String(320)
        elif col.type == "inn":
            dtype = String(12)
        elif col.type == "kpp":
            dtype = String(9)
        elif col.type == "ogrn":
            dtype = String(15)
        elif col.type == "enum":
            dtype = String(128)
        elif col.type == "json":
            dtype = JSONB
        else:
            dtype = Text
        columns.append(Column(col.target_field, dtype, nullable=col.nullable))

    technical = [
        Column("_ingest_run_id", BIGINT, nullable=True),
        Column("_ingest_extracted_at", DateTime(timezone=True), nullable=True),
        Column("_ingest_loaded_at", DateTime(timezone=True), nullable=False, server_default=text("NOW()")),
        Column("_source_record_id", Text, nullable=True),
    ]
    if keep_raw_payload:
        technical.append(Column("_raw", JSONB, nullable=True))

    constraints = []
    if stream_rules.primary_key:
        constraints.append(PrimaryKeyConstraint(*stream_rules.primary_key))
    else:
        surrogate_name = "id"
        if any(c.name == "id" for c in columns):
            surrogate_name = "_surrogate_id"
        technical.insert(0, Column(surrogate_name, BIGINT, primary_key=True, autoincrement=True))

    return Table(
        table_name,
        metadata,
        *columns,
        *technical,
        *constraints,
        schema=schema,
    )


def validate_stream_rules_compatible(old: StreamRules, new: StreamRules) -> None:
    """Проверяет, можно ли эволюционировать схему без recreate stream."""
    old_map = {c.target_field: c.type for c in old.columns}
    new_map = {c.target_field: c.type for c in new.columns}
    for col_name, old_type in old_map.items():
        if col_name in new_map and new_map[col_name] != old_type:
            raise ValueError(f"recreate stream required: column {col_name} type changed {old_type} -> {new_map[col_name]}")
