"""Фаза B: персистенция raw-слоя в PostgreSQL до нормализации."""

from __future__ import annotations

import dagster as dg

from datanorma.resources.database import PostgresResource
from datanorma.warehouse.raw_staging import load_raw_to_staging


@dg.asset(
    group_name="staging",
    compute_kind="postgres",
    description="Сырой слой в БД: raw_<source>_<stream>_staging с _ingest_* мета-колонками и sync_state (Ingest-style).",
    retry_policy=dg.RetryPolicy(max_retries=2, delay=5),
)
def staging_raw_postgres(
    raw_google_sheet_orders: dict,
    raw_bitrix24_crm_deals: dict,
    postgres: PostgresResource,
) -> dict:
    engine = postgres.get_engine()
    return load_raw_to_staging(
        engine,
        raw_payloads=[raw_google_sheet_orders, raw_bitrix24_crm_deals],
    )
