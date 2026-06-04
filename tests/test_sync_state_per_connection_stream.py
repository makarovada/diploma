"""sync_state must be per connection_stream, not shared by integration_code+stream_name."""

from __future__ import annotations

import pytest

from datanorma.web import elt_repo as repo

pytestmark = pytest.mark.unit


class _ExecuteResult:
    def __init__(self, rows: list[dict] | None = None) -> None:
        self._rows = rows or []

    def first(self):
        return self._rows[0] if self._rows else None


def test_ensure_sync_state_inserts_separate_rows_per_connection_stream() -> None:
    calls: list[tuple] = []

    def _execute(stmt, params=None):
        calls.append((str(stmt), params or {}))
        if "SELECT id FROM sync_state WHERE connection_stream_id" in str(stmt):
            csid = (params or {}).get("csid")
            if csid == 10:
                return _ExecuteResult([{"id": 99}])
            return _ExecuteResult()
        return _ExecuteResult()

    conn = type("C", (), {"execute": staticmethod(_execute)})()

    repo.ensure_sync_state_for_stream(
        conn,
        integration_code="google_sheet",
        stream_name="orders",
        sync_mode="full_refresh",
        cursor_field=None,
        connection_stream_id=10,
        workspace_id=1,
    )
    repo.ensure_sync_state_for_stream(
        conn,
        integration_code="google_sheet",
        stream_name="orders",
        sync_mode="incremental",
        cursor_field="order_id",
        connection_stream_id=11,
        workspace_id=1,
    )

    inserts = [c for c in calls if "INSERT INTO sync_state" in c[0]]
    updates = [c for c in calls if "UPDATE sync_state" in c[0]]
    assert len(updates) == 1
    assert len(inserts) == 1
    assert inserts[0][1]["csid"] == 11
