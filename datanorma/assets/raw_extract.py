"""Единый extract raw-слоя для Dagster assets (Bitrix24, Google Sheets, …)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from datanorma.resources.paths import DataPathsResource
from datanorma.sources.registry import create_source


def extract_raw_stream(
    sync_catalog: dict[str, Any],
    paths: DataPathsResource,
    *,
    integration_code: str,
    stream_name: str,
) -> dict[str, Any]:
    """Читает поток источника и возвращает унифицированный raw payload для staging."""
    stream_cfg = (sync_catalog.get("streams") or {}).get(integration_code) or {}
    src = create_source(integration_code, paths=paths)
    records = list(
        src.read(
            stream_name,
            sync_mode=str(stream_cfg.get("sync_mode") or "full_refresh"),
            cursor_field=stream_cfg.get("cursor_field"),
            last_cursor=stream_cfg.get("last_cursor"),
        )
    )
    ingest_mode = getattr(src, "last_ingest_mode", f"{integration_code}_api")
    source_ref = getattr(src, "last_source_ref", "") or ""

    return {
        "source_system": integration_code,
        "stream_name": stream_name,
        "ingest_mode": ingest_mode,
        "source_ref": source_ref,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "row_count": len(records),
        "rows": records,
    }
