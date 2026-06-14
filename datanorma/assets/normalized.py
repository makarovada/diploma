import dagster as dg

from datanorma.ingest.dagster_streams import DAGSTER_WAREHOUSE_STREAMS
from datanorma.normalization.apply import apply_rules_to_batch
from datanorma.normalization.typing import upsert_rows
from datanorma.normalization.default_stream_rules import default_stream_rules_from_json_schema
from datanorma.sources.registry import create_source
from datanorma.resources.database import PostgresResource
from datanorma.resources.paths import DataPathsResource
from datanorma.sources.schema_inference import records_to_json_schema
from datanorma.warehouse.tables import ensure_normalized_table


def _normalize_raw_payload(
    raw_payload: dict,
    *,
    paths: DataPathsResource,
    engine,
) -> tuple[list[dict], int, dict[str, int]]:
    connector_code = str(raw_payload.get("source_system") or "")
    stream_name = str(raw_payload.get("stream_name") or "")
    source_rows = raw_payload.get("rows") or []
    src = create_source(connector_code, paths=paths)
    json_schema = records_to_json_schema(source_rows[:50] if source_rows else [])
    if hasattr(src, "default_stream_rules"):
        rules = src.default_stream_rules(stream_name=stream_name, json_schema=json_schema)  # type: ignore[attr-defined]
    else:
        rules = default_stream_rules_from_json_schema(stream_name=stream_name, json_schema=json_schema)
    typed_rows, issues, batch_stats = apply_rules_to_batch(rules, source_rows)
    table = ensure_normalized_table(connector_code=connector_code, stream_rules=rules)
    upsert_rows(engine, table, typed_rows, primary_key=rules.primary_key)
    stats = {"rows_in": batch_stats.rows_in, "rows_out": batch_stats.rows_out}
    return typed_rows, len(issues), stats


@dg.asset(
    group_name="normalized",
    description="Нормализация по правилам колонок и загрузка в normalized.* (Google Sheets + Bitrix24).",
)
def normalized_orders(
    raw_google_sheet_orders: dict,
    raw_bitrix24_crm_deals: dict,
    staging_raw_postgres: dict,
    postgres: PostgresResource,
    paths: DataPathsResource,
) -> dict:
    _ = staging_raw_postgres
    engine = postgres.get_engine()
    rows: list[dict] = []
    issues_total = 0
    stats = {"rows_in": 0, "rows_out": 0}
    raw_row_counts: dict[str, int] = {}

    raw_by_code = {
        raw_google_sheet_orders.get("source_system"): raw_google_sheet_orders,
        raw_bitrix24_crm_deals.get("source_system"): raw_bitrix24_crm_deals,
    }
    for stream in DAGSTER_WAREHOUSE_STREAMS:
        raw_payload = raw_by_code.get(stream.integration_code)
        if raw_payload is None:
            continue
        typed_rows, issue_count, batch_stats = _normalize_raw_payload(
            raw_payload,
            paths=paths,
            engine=engine,
        )
        rows.extend(typed_rows)
        issues_total += issue_count
        stats["rows_in"] += batch_stats["rows_in"]
        stats["rows_out"] += batch_stats["rows_out"]
        raw_row_counts[stream.integration_code] = int(raw_payload.get("row_count") or 0)

    return {
        "rows": rows,
        "stats": stats,
        "issues": issues_total,
        "raw_row_counts": raw_row_counts,
    }
