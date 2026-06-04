from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from datanorma.web.norm_issues import _public_row, list_norm_issues_for_run

pytestmark = pytest.mark.unit


def test_public_row_maps_elt_columns() -> None:
    row = _public_row(
        {
            "id": 5,
            "sync_run_id": 1544,
            "connection_id": 19,
            "stream_name": "crm_deals",
            "target_field": "STAGE_ID",
            "error_code": "cast_error",
            "error_text": "invalid literal",
            "source_system": "bitrix24",
            "connection_name": "Bitrix Пример",
            "status": "open",
        }
    )
    assert row["field_name"] == "STAGE_ID"
    assert row["issue_type"] == "cast_error"
    assert row["message"] == "invalid literal"
    assert row["stream_name"] == "crm_deals"


def test_list_norm_issues_for_run_builds_query() -> None:
    captured: list = []

    def _execute(stmt, params=None):
        captured.append((str(stmt), params))
        return MagicMock(mappings=lambda: MagicMock(all=lambda: []))

    conn = MagicMock()
    conn.execute = _execute
    list_norm_issues_for_run(conn, sync_run_id=1544, limit=10)
    assert "sync_run_id = :rid" in captured[0][0]
