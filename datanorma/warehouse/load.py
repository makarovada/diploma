"""Загрузка типизированных строк в динамические таблицы normalized.*."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.engine import Engine

from datanorma.normalization.rules import StreamRules
from datanorma.normalization.typing import upsert_rows
from datanorma.warehouse.tables import ensure_normalized_table


def load_normalized_stream_to_postgres(
    engine: Engine,
    *,
    connector_code: str,
    stream_rules: StreamRules,
    rows: list[dict[str, Any]],
    chunk_size: int = 500,
) -> dict[str, Any]:
    table = ensure_normalized_table(connector_code=connector_code, stream_rules=stream_rules)
    now = datetime.now(timezone.utc)
    payloads = [{**r, "_ingest_loaded_at": now} for r in rows]
    info = upsert_rows(engine, table, payloads, primary_key=stream_rules.primary_key, chunk_size=chunk_size)
    return {"table": f"{table.schema}.{table.name}", "rows_upserted": info.get("rows_upserted", 0)}


def count_rows(engine: Engine, *, schema: str, table_name: str) -> int:
    from sqlalchemy import MetaData, Table

    meta = MetaData()
    table = Table(table_name, meta, schema=schema, autoload_with=engine)
    with engine.connect() as conn:
        q = select(func.count()).select_from(table)
        return int(conn.execute(q).scalar_one())
