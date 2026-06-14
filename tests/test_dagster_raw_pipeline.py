"""Unit-тесты единого Dagster raw extract и staging."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from datanorma.assets.raw_extract import extract_raw_stream
from datanorma.ingest.dagster_streams import DAGSTER_WAREHOUSE_STREAMS, dagster_staging_table_names
from datanorma.ingest.stream_config import parse_all_stream_configs
from datanorma.resources.paths import DataPathsResource
from datanorma.warehouse.raw_staging import load_raw_to_staging

pytestmark = pytest.mark.unit


def test_dagster_streams_include_bitrix_and_sheets() -> None:
    codes = {s.integration_code for s in DAGSTER_WAREHOUSE_STREAMS}
    assert codes == {"google_sheet", "bitrix24"}
    assert dagster_staging_table_names() == [
        "raw_google_sheet_orders_staging",
        "raw_bitrix24_crm_deals_staging",
    ]


def test_parse_all_stream_configs_includes_bitrix24() -> None:
    cfg = parse_all_stream_configs()
    assert "bitrix24" in cfg
    assert cfg["bitrix24"]["stream"] == "crm_deals"
    assert cfg["bitrix24"]["table"] == "raw_bitrix24_crm_deals_staging"


def test_extract_raw_stream_bitrix_fixture(tmp_path) -> None:
    paths = DataPathsResource(repo_root=str(tmp_path))
    payload = extract_raw_stream(
        {"streams": {"bitrix24": {"sync_mode": "full_refresh"}}},
        paths,
        integration_code="bitrix24",
        stream_name="crm_deals",
    )
    assert payload["source_system"] == "bitrix24"
    assert payload["stream_name"] == "crm_deals"
    assert payload["ingest_mode"] == "fixture_json"
    assert payload["row_count"] >= 1


@patch("datanorma.warehouse.raw_staging.ensure_phase1_schema")
@patch("datanorma.warehouse.raw_staging.ensure_raw_staging_table")
def test_load_raw_to_staging_multiple_payloads(_ensure_table: MagicMock, _schema: MagicMock) -> None:
    conn = MagicMock()

    @contextmanager
    def _begin():
        yield conn

    engine = MagicMock()
    engine.begin = _begin

    payloads = [
        {
            "source_system": "google_sheet",
            "stream_name": "orders",
            "rows": [{"x": 1}],
            "ingest_mode": "fixture_csv",
        },
        {
            "source_system": "bitrix24",
            "stream_name": "crm_deals",
            "rows": [{"ID": "1"}],
            "ingest_mode": "fixture_json",
        },
    ]

    out = load_raw_to_staging(engine, raw_payloads=payloads)

    assert out["rows_written"] == {"google_sheet": 1, "bitrix24": 1}
    assert out["sheet_rows_written"] == 2
    # 2 row inserts + 2 sync_state upserts
    assert conn.execute.call_count == 4
