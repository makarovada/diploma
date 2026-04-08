"""Сырой слой: Google Sheets (service account) или CSV-экспорт из samples."""

from __future__ import annotations

from datetime import datetime, timezone

import dagster as dg

from datanorma.resources.paths import DataPathsResource
from datanorma.sources.sheets import GoogleSheetsSource


@dg.asset(
    group_name="raw",
    description="Таблица продаж: GSPREAD_* или data/samples/google_sheet_export.csv. Режим sync из YAML.",
    compute_kind="google_sheets",
    retry_policy=dg.RetryPolicy(max_retries=3, delay=10),
)
def raw_google_sheet_orders(sync_catalog: dict, paths: DataPathsResource) -> dict:
    src = GoogleSheetsSource(paths)
    sh = (sync_catalog.get("streams") or {}).get("google_sheet") or {}
    records = list(
        src.read(
            "orders",
            sync_mode=str(sh.get("sync_mode") or "full_refresh"),
            cursor_field=sh.get("cursor_field"),
            last_cursor=sh.get("last_cursor"),
        )
    )
    ingest_mode = src.last_ingest_mode
    source_ref = src.last_source_ref

    return {
        "source_system": "google_sheet",
        "ingest_mode": ingest_mode,
        "source_ref": source_ref,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "row_count": len(records),
        "rows": records,
    }
