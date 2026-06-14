"""Unit-тесты записи raw в staging (без реального PostgreSQL)."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from datanorma.warehouse.raw_staging import load_raw_to_staging

pytestmark = pytest.mark.unit


@patch("datanorma.warehouse.raw_staging.ensure_phase1_schema")
@patch("datanorma.warehouse.raw_staging.ensure_raw_staging_table")
def test_load_raw_to_staging_execute_count(_ensure_table: MagicMock, _schema: MagicMock) -> None:
    conn = MagicMock()

    @contextmanager
    def _begin():
        yield conn

    engine = MagicMock()
    engine.begin = _begin

    raw_sheet = {"rows": [{"x": 1}, {"y": 2}]}

    out = load_raw_to_staging(engine, raw_sheet=raw_sheet)

    assert out["sheet_rows_written"] == 2
    assert "ingest_batch_id" in out
    # 2 sheet rows + 1 sync_state
    assert conn.execute.call_count == 3
