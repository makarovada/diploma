"""Сырой слой: выгрузка 1С (CSV/Excel из файла по умолчанию — sample)."""

from __future__ import annotations

from datetime import datetime, timezone

import logging

import dagster as dg

from datanorma.resources.paths import DataPathsResource
from datanorma.sources.onec import OneCSource

_log = logging.getLogger(__name__)


@dg.asset(
    group_name="raw",
    description="Документы продаж 1С: DATANORMA_1C_EXPORT_PATH или data/samples/1c_export.csv. Режим sync из YAML.",
    compute_kind="file",
    retry_policy=dg.RetryPolicy(max_retries=2, delay=5),
)
def raw_1c_orders(sync_catalog: dict, paths: DataPathsResource) -> dict:
    src = OneCSource(paths)
    c1 = (sync_catalog.get("streams") or {}).get("1c") or {}
    records = list(
        src.read(
            "orders",
            sync_mode=str(c1.get("sync_mode") or "full_refresh"),
            cursor_field=c1.get("cursor_field"),
            last_cursor=c1.get("last_cursor"),
        )
    )
    ingest_mode = src.last_ingest_mode
    path = src.resolved_export_path()

    _log.info("1С: строк %s из %s", len(records), path)

    return {
        "source_system": "1c",
        "ingest_mode": ingest_mode,
        "source_path": str(path.resolve()),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "row_count": len(records),
        "columns": src.last_columns or (list(records[0].keys()) if records else []),
        "rows": records,
    }
