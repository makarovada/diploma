"""Фаза B: персистенция raw-слоя в PostgreSQL до нормализации."""

from __future__ import annotations

import dagster as dg

from datanorma.resources.database import PostgresResource
from datanorma.warehouse.raw_staging import load_raw_to_staging


@dg.asset(
    group_name="staging",
    compute_kind="postgres",
    description="Сырой слой в БД: raw_ozon_staging / raw_1c_staging / raw_sheet_staging и sync_state.",
)
def staging_raw_postgres(
    raw_ozon_postings: dict,
    raw_1c_orders: dict,
    raw_google_sheet_orders: dict,
    postgres: PostgresResource,
) -> dict:
    engine = postgres.get_engine()
    return load_raw_to_staging(
        engine,
        raw_ozon=raw_ozon_postings,
        raw_1c=raw_1c_orders,
        raw_sheet=raw_google_sheet_orders,
    )
