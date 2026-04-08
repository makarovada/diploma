"""Unit-тесты записи raw в staging (без реального PostgreSQL)."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from datanorma.warehouse.raw_staging import load_raw_to_staging


@patch("datanorma.warehouse.raw_staging.ensure_phase1_schema")
def test_load_raw_to_staging_execute_count(_schema: MagicMock) -> None:
    conn = MagicMock()

    @contextmanager
    def _begin():
        yield conn

    engine = MagicMock()
    engine.begin = _begin

    raw_ozon = {"postings": [{"a": 1}, {"b": 2}]}
    raw_1c = {"rows": [{"x": 1}]}
    raw_sheet = {"rows": []}

    out = load_raw_to_staging(engine, raw_ozon=raw_ozon, raw_1c=raw_1c, raw_sheet=raw_sheet)

    assert out["ozon_rows_written"] == 2
    assert out["onec_rows_written"] == 1
    assert out["sheet_rows_written"] == 0
    assert "ingest_batch_id" in out
    # 2 oz + 1 1c + 0 sheet + 3 sync_state
    assert conn.execute.call_count == 6
