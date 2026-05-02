import dagster as dg

from datanorma.resources.database import PostgresResource
from datanorma.warehouse.load import count_canonical_sales, load_canonical_sales_to_postgres


@dg.asset(
    group_name="warehouse",
    description="Загрузка витрины canonical_sales (UPSERT; обновление только если _ingest_loaded_at не старее существующей).",
)
def warehouse_sales(typed_canonical_sales: dict, normalized_orders: dict, postgres: PostgresResource) -> dict:
    rows = typed_canonical_sales.get("rows") or normalized_orders.get("rows") or []
    engine = postgres.get_engine()
    load_info = load_canonical_sales_to_postgres(engine, rows)
    total = count_canonical_sales(engine)
    return {
        "status": "ok",
        "canonical_schema": normalized_orders.get("canonical_schema"),
        **load_info,
        "table_rowcount": total,
    }
