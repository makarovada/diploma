"""Сырой слой: Google Sheets (service account) или CSV-экспорт из samples."""

from __future__ import annotations

import dagster as dg

from datanorma.assets.raw_extract import extract_raw_stream
from datanorma.ingest.dagster_streams import DAGSTER_WAREHOUSE_STREAMS
from datanorma.resources.paths import DataPathsResource

_GOOGLE_SHEET_STREAM = next(s for s in DAGSTER_WAREHOUSE_STREAMS if s.integration_code == "google_sheet")


@dg.asset(
    group_name="raw",
    name=_GOOGLE_SHEET_STREAM.raw_asset_name,
    description=_GOOGLE_SHEET_STREAM.description,
    compute_kind=_GOOGLE_SHEET_STREAM.compute_kind,
    retry_policy=dg.RetryPolicy(max_retries=3, delay=10),
)
def raw_google_sheet_orders(sync_catalog: dict, paths: DataPathsResource) -> dict:
    return extract_raw_stream(
        sync_catalog,
        paths,
        integration_code=_GOOGLE_SHEET_STREAM.integration_code,
        stream_name=_GOOGLE_SHEET_STREAM.stream_name,
    )
