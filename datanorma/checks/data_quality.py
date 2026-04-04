"""Проверки после материализации: непустая витрина, загрузка в warehouse."""

from __future__ import annotations

import dagster as dg

from datanorma.assets.normalized import normalized_orders
from datanorma.assets.staging_postgres import staging_raw_postgres
from datanorma.assets.warehouse import warehouse_sales


@dg.asset_check(
    asset=staging_raw_postgres,
    description="В staging записан хотя бы один сырой объект (Ozon/1С/лист).",
)
def staging_raw_has_rows(staging_raw_postgres: dict) -> dg.AssetCheckResult:
    n = (
        int(staging_raw_postgres.get("ozon_rows_written") or 0)
        + int(staging_raw_postgres.get("onec_rows_written") or 0)
        + int(staging_raw_postgres.get("sheet_rows_written") or 0)
    )
    return dg.AssetCheckResult(
        passed=n > 0,
        metadata={"staging_rows_total": dg.MetadataValue.int(n)},
        severity=dg.AssetCheckSeverity.WARN,
    )


@dg.asset_check(asset=normalized_orders, description="В канонической витрине есть хотя бы одна строка.")
def normalized_orders_has_rows(normalized_orders: dict) -> dg.AssetCheckResult:
    rows = normalized_orders.get("rows") or []
    n = len(rows)
    return dg.AssetCheckResult(
        passed=n > 0,
        metadata={"row_count": dg.MetadataValue.int(n)},
        severity=dg.AssetCheckSeverity.WARN,
    )


@dg.asset_check(asset=warehouse_sales, description="В PostgreSQL записана хотя бы одна строка витрины.")
def warehouse_has_rows(warehouse_sales: dict) -> dg.AssetCheckResult:
    total = int(warehouse_sales.get("table_rowcount") or 0)
    upserted = int(warehouse_sales.get("rows_upserted") or 0)
    return dg.AssetCheckResult(
        passed=total > 0 and upserted > 0,
        metadata={
            "table_rowcount": dg.MetadataValue.int(total),
            "rows_upserted": dg.MetadataValue.int(upserted),
        },
        severity=dg.AssetCheckSeverity.WARN,
    )
