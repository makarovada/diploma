"""Unit tests: run_connection_sync stream filter and cooperative cancel."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from datanorma.elt import run_connection_sync as rcs
from datanorma.web.sync_runs import SyncCancelled

pytestmark = pytest.mark.unit


def _connection_with_streams(*names: str) -> dict:
    return {
        "source_id": 1,
        "destination_id": 2,
        "streams": [
            {
                "id": i + 1,
                "stream_name": name,
                "is_enabled": True,
                "sync_mode": "full_refresh",
                "destination_sync_mode": "refresh_overwrite",
                "cursor_field": None,
                "primary_key": None,
            }
            for i, name in enumerate(names)
        ],
    }


def test_only_stream_name_filters_enabled_streams(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = MagicMock()
    monkeypatch.setattr(rcs, "get_connection", lambda *_a, **_k: _connection_with_streams("orders", "customers"))
    monkeypatch.setattr(rcs, "get_source", lambda *_a, **_k: {"connector_code": "google_sheet", "config_encrypted": "{}"})
    monkeypatch.setattr(rcs, "get_destination", lambda *_a, **_k: {"connector_code": "postgres", "config_encrypted": "{}"})
    monkeypatch.setattr(rcs, "public_source_payload", lambda _r: {"connector_code": "google_sheet", "config": {}})
    monkeypatch.setattr(rcs, "public_destination_payload", lambda _r: {"connector_code": "postgres", "config": {}})

    processed: list[str] = []

    class _Src:
        def read(self, stream_name, **_k):
            processed.append(stream_name)
            return [{"id": 1}]

    monkeypatch.setattr(rcs, "create_source", lambda *_a, **_k: _Src())
    monkeypatch.setattr(rcs, "load_stream_rules_for_sync", lambda *_a, **_k: None)

    ss_row = {
        "id": 1,
        "integration_code": "google_sheet",
        "stream_name": "orders",
        "sync_mode": "full_refresh",
        "cursor_field": None,
        "cursor_value": "{}",
        "ingest_state": {},
    }

    def _execute(stmt, params=None):
        m = MagicMock()
        m.mappings.return_value.first.return_value = ss_row
        return m

    conn.execute = _execute
    monkeypatch.setattr(
        rcs,
        "destination_write",
        lambda *_a, **_k: MagicMock(ok=True, rows_written=1, message="ok"),
    )

    summary = rcs.run_connection_sync(
        conn,
        workspace_id=1,
        domain_connection_id=1,
        only_stream_name="customers",
    )
    assert processed == ["customers"]
    assert len(summary["streams"]) == 1
    assert summary["streams"][0]["stream_name"] == "customers"


def test_run_connection_sync_raises_sync_cancelled(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = MagicMock()
    monkeypatch.setattr(rcs, "get_connection", lambda *_a, **_k: _connection_with_streams("a", "b"))
    monkeypatch.setattr(rcs, "get_source", lambda *_a, **_k: {"connector_code": "google_sheet", "config_encrypted": "{}"})
    monkeypatch.setattr(rcs, "get_destination", lambda *_a, **_k: {"connector_code": "postgres", "config_encrypted": "{}"})
    monkeypatch.setattr(rcs, "public_source_payload", lambda _r: {"connector_code": "google_sheet", "config": {}})
    monkeypatch.setattr(rcs, "public_destination_payload", lambda _r: {"connector_code": "postgres", "config": {}})

    class _Src:
        def read(self, stream_name, **_k):
            return [{"id": stream_name}]

    monkeypatch.setattr(rcs, "create_source", lambda *_a, **_k: _Src())
    monkeypatch.setattr(rcs, "load_stream_rules_for_sync", lambda *_a, **_k: None)
    monkeypatch.setattr(
        rcs,
        "destination_write",
        lambda *_a, **_k: MagicMock(ok=True, rows_written=1, message="ok"),
    )

    ss_row = {
        "id": 1,
        "integration_code": "google_sheet",
        "stream_name": "a",
        "sync_mode": "full_refresh",
        "cursor_field": None,
        "cursor_value": "{}",
        "ingest_state": {},
    }

    def _execute(stmt, params=None):
        m = MagicMock()
        m.mappings.return_value.first.return_value = ss_row
        return m

    conn.execute = _execute

    checks = {"n": 0}

    def _cancel_requested(_conn, _run_id):
        checks["n"] += 1
        return checks["n"] > 1

    monkeypatch.setattr(rcs, "is_sync_run_cancel_requested", _cancel_requested)

    with pytest.raises(SyncCancelled) as exc:
        rcs.run_connection_sync(conn, workspace_id=1, domain_connection_id=1, sync_run_id=99)
    assert exc.value.summary["cancelled"] is True
    assert len(exc.value.summary["streams"]) == 1
