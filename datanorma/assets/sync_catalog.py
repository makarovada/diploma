"""Загрузка каталога потоков и sync_state из БД перед raw-синхронизацией (как read state в Ingest)."""

from __future__ import annotations

from datetime import datetime, timezone

import dagster as dg

from datanorma.ingest.stream_config import parse_all_stream_configs
from datanorma.resources.database import PostgresResource
from datanorma.warehouse.sync_state_repo import extract_stream_cursor, fetch_sync_state_map


@dg.asset(
    group_name="sync",
    compute_kind="postgres",
    description="Каталог потоков + последнее sync_state из PostgreSQL (перед raw assets).",
)
def sync_catalog(postgres: PostgresResource) -> dict:
    yaml_streams = parse_all_stream_configs()
    engine = postgres.get_engine()
    db_map = fetch_sync_state_map(engine)

    streams_out: dict[str, dict] = {}
    for code, ycfg in yaml_streams.items():
        stream_name = ycfg["stream"]
        db_row = db_map.get((code, stream_name)) or db_map.get((code, "default"))
        last_cursor = extract_stream_cursor(db_row) if db_row else None
        streams_out[code] = {
            **ycfg,
            "last_cursor": last_cursor,
            "has_db_row": db_row is not None,
            "resume_from_state": bool(last_cursor),
        }

    return {
        "catalog_loaded_at": datetime.now(timezone.utc).isoformat(),
        "mappings_version": "rules_v1",
        "streams": streams_out,
    }
