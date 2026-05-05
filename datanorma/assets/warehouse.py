"""Совместимый alias asset для проверок качества."""

from __future__ import annotations

import dagster as dg


@dg.asset(group_name="warehouse", description="Совместимый alias для нового normalized-пайплайна.")
def warehouse_sales(normalized_orders: dict) -> dict:
    """Возвращает статистику normalized-слоя."""
    return {
        "status": "ok",
        "rows_upserted": len(normalized_orders.get("rows") or []),
        "stats": normalized_orders.get("stats") or {},
    }
