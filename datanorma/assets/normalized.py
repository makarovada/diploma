import dagster as dg

from datanorma.normalization.apply import apply_rules_to_batch
from datanorma.normalization.typing import upsert_rows
from datanorma.normalization.default_stream_rules import default_stream_rules_from_json_schema
from datanorma.sources.registry import create_source
from datanorma.resources.database import PostgresResource
from datanorma.resources.paths import DataPathsResource
from datanorma.sources.schema_inference import records_to_json_schema
from datanorma.warehouse.tables import ensure_normalized_table


@dg.asset(
    group_name="normalized",
    description="Нормализация по правилам колонок и загрузка в normalized.*",
)
def normalized_orders(
    raw_ozon_postings: dict,
    raw_1c_orders: dict,
    raw_google_sheet_orders: dict,
    staging_raw_postgres: dict,
    postgres: PostgresResource,
    paths: DataPathsResource,
) -> dict:
    _ = staging_raw_postgres
    engine = postgres.get_engine()
    rows = []
    issues_total = 0
    stats = {"rows_in": 0, "rows_out": 0}

    packs = [
        ("ozon", "postings", raw_ozon_postings.get("postings") or []),
        ("1c", "orders", raw_1c_orders.get("rows") or []),
        ("google_sheet", "orders", raw_google_sheet_orders.get("rows") or []),
    ]
    for connector_code, stream_name, source_rows in packs:
        src = create_source(connector_code, paths=paths)
        json_schema = records_to_json_schema(source_rows[:50] if source_rows else [])
        if hasattr(src, "default_stream_rules"):
            rules = src.default_stream_rules(stream_name=stream_name, json_schema=json_schema)  # type: ignore[attr-defined]
        else:
            rules = default_stream_rules_from_json_schema(stream_name=stream_name, json_schema=json_schema)
        typed_rows, issues, batch_stats = apply_rules_to_batch(rules, source_rows)
        table = ensure_normalized_table(connector_code=connector_code, stream_rules=rules)
        upsert_rows(engine, table, typed_rows, primary_key=rules.primary_key)
        rows.extend(typed_rows)
        issues_total += len(issues)
        stats["rows_in"] += batch_stats.rows_in
        stats["rows_out"] += batch_stats.rows_out

    return {
        "rows": rows,
        "stats": stats,
        "issues": issues_total,
        "raw_row_counts": {
            "ozon": raw_ozon_postings["row_count"],
            "1c": raw_1c_orders["row_count"],
            "google_sheet": raw_google_sheet_orders["row_count"],
        },
    }
