import dagster as dg

from datanorma.resources.database import PostgresResource
from datanorma.warehouse.load import count_canonical_sales, load_canonical_sales_to_postgres


@dg.asset(
    group_name="warehouse",
    description="Загрузка витрины canonical_sales в PostgreSQL (UPSERT по source_system + source_record_id).",
)
def warehouse_sales(normalized_orders: dict, postgres: PostgresResource) -> dict:
    rows = normalized_orders.get("rows") or []
    engine = postgres.get_engine()
    load_info = load_canonical_sales_to_postgres(engine, rows)
    total = count_canonical_sales(engine)
    return {
        "status": "ok",
        "canonical_schema": normalized_orders.get("canonical_schema"),
        **load_info,
        "table_rowcount": total,
    }
