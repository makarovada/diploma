"""Сырой слой: Bitrix24 CRM (webhook или фикстуры)."""

from __future__ import annotations

import dagster as dg

from datanorma.assets.raw_extract import extract_raw_stream
from datanorma.ingest.dagster_streams import DAGSTER_WAREHOUSE_STREAMS
from datanorma.resources.paths import DataPathsResource

_BITRIX_STREAM = next(s for s in DAGSTER_WAREHOUSE_STREAMS if s.integration_code == "bitrix24")


@dg.asset(
    group_name="raw",
    name=_BITRIX_STREAM.raw_asset_name,
    description=_BITRIX_STREAM.description,
    compute_kind=_BITRIX_STREAM.compute_kind,
    retry_policy=dg.RetryPolicy(max_retries=3, delay=10),
)
def raw_bitrix24_crm_deals(sync_catalog: dict, paths: DataPathsResource) -> dict:
    return extract_raw_stream(
        sync_catalog,
        paths,
        integration_code=_BITRIX_STREAM.integration_code,
        stream_name=_BITRIX_STREAM.stream_name,
    )
