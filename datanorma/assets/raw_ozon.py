"""Сырой слой: Ozon Seller API (при наличии ключей) или локальная выборка JSON."""

from __future__ import annotations

from datetime import datetime, timezone

import logging

import dagster as dg

from datanorma.resources.paths import DataPathsResource
from datanorma.sources.ozon import OzonSource

_log = logging.getLogger(__name__)


@dg.asset(
    group_name="raw",
    description="Отправления Ozon (FBS list). Без OZON_CLIENT_ID/OZON_API_KEY — из data/samples. "
    "Режим incremental/full_refresh из YAML (sync_catalog).",
    compute_kind="ozon_api",
    retry_policy=dg.RetryPolicy(max_retries=3, delay=10),
)
def raw_ozon_postings(sync_catalog: dict, paths: DataPathsResource) -> dict:
    oz_stream = (sync_catalog.get("streams") or {}).get("ozon") or {}
    sync_mode = oz_stream.get("sync_mode") or "full_refresh"
    cursor_field = oz_stream.get("cursor_field")
    last_cursor = oz_stream.get("last_cursor")

    src = OzonSource(paths)
    postings = list(
        src.read(
            "postings",
            sync_mode=str(sync_mode),
            cursor_field=cursor_field,
            last_cursor=last_cursor,
        )
    )
    ingest_mode = src.last_ingest_mode
    _log.info("Ozon: режим %s, отправлений %s", ingest_mode, len(postings))

    return {
        "source_system": "ozon",
        "ingest_mode": ingest_mode,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "row_count": len(postings),
        "postings": postings,
    }
