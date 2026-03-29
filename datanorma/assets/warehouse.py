import dagster as dg
from sqlalchemy import text

from datanorma.resources.database import PostgresResource


@dg.asset(
    group_name="warehouse",
    description="Загрузка в warehouse (этап 1–2: проверка БД; далее INSERT/merge витрины).",
)
def warehouse_sales(normalized_orders: dict, postgres: PostgresResource) -> dict:
    with postgres.get_engine().connect() as conn:
        conn.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "upstream_keys": list(normalized_orders.keys()),
    }
