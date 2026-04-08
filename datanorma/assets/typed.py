"""Typed layer (TyD-like): cast canonical rows to strict SQL types."""

from __future__ import annotations

import dagster as dg

from datanorma.normalization.typing import cast_rows_to_typed, count_typed_rows, load_canonical_schema, upsert_typed_rows
from datanorma.resources.database import PostgresResource


@dg.asset(
    group_name="typed",
    description="Typing & deduping: canonical rows -> typed_canonical_sales with _airbyte_meta.changes",
)
def typed_canonical_sales(normalized_orders: dict, postgres: PostgresResource) -> dict:
    rows = normalized_orders.get("rows") or []
    schema = load_canonical_schema()
    typed_rows, typing_stats = cast_rows_to_typed(rows, schema)
    engine = postgres.get_engine()
    load_info = upsert_typed_rows(engine, typed_rows)
    total = count_typed_rows(engine)
    return {
        "status": "ok",
        "rows": typed_rows,
        "typing_stats": typing_stats,
        **load_info,
        "table_rowcount": total,
    }
