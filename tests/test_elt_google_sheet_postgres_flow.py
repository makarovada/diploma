"""ELT: Google Sheets (mock gspread) → PostgreSQL sink через run_connection_sync."""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, text

from datanorma.elt.run_connection_sync import run_connection_sync

pytestmark = pytest.mark.integration

SINK_CONFIG = {
    "url": os.environ.get(
        "TEST_SINK_URL",
        "postgresql://test_user:test_pass@127.0.0.1:5544/test_sink",
    ),
    "schema": "public",
    "table": "elt_test_load",
}

SAMPLE_ROWS = [
    {
        "order_id": "GS-E2E-001",
        "order_date": "2025-01-01",
        "customer_name": "E2E Test",
        "amount": "99.00",
        "currency": "RUB",
        "channel": "online",
    },
]


def _sink_reachable() -> bool:
    try:
        from datanorma.destinations.postgres import _normalize_postgres_url

        url = _normalize_postgres_url(SINK_CONFIG["url"])
        eng = create_engine(url, pool_pre_ping=True)
        with eng.connect() as c:
            c.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@pytest.fixture
def mock_gspread(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_load(sa_info: dict, spreadsheet_id: str, worksheet: str | int):
        return list(SAMPLE_ROWS)

    monkeypatch.setattr("datanorma.sources.sheets._load_via_gspread_info", _fake_load)


@pytest.fixture
def mock_elt_repo(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    rcs_mod = sys.modules["datanorma.elt.run_connection_sync"]
    conn = MagicMock()
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
        s = str(stmt)
        m = MagicMock()
        if "FROM sync_state" in s:
            m.mappings.return_value.first.return_value = ss_row
        return m

    conn.execute = _execute

    monkeypatch.setattr(
        rcs_mod,
        "get_connection",
        lambda *_a, **_k: {
            "id": 1,
            "source_id": 10,
            "destination_id": 20,
            "streams": [
                {
                    "id": 100,
                    "stream_name": "orders",
                    "sync_mode": "full_refresh",
                    "cursor_field": None,
                    "is_enabled": True,
                }
            ],
        },
    )
    monkeypatch.setattr(
        rcs_mod,
        "get_source",
        lambda *_a, **_k: {"id": 10, "connector_code": "google_sheet", "config_encrypted": "{}"},
    )
    monkeypatch.setattr(
        rcs_mod,
        "get_destination",
        lambda *_a, **_k: {"id": 20, "connector_code": "postgres", "config_encrypted": "{}"},
    )
    monkeypatch.setattr(
        rcs_mod,
        "public_source_payload",
        lambda _r: {
            "connector_code": "google_sheet",
            "config": {
                "spreadsheet_id": "sheet-e2e",
                "worksheet": "0",
                "service_account_json": {"type": "service_account", "project_id": "e2e"},
            },
        },
    )
    monkeypatch.setattr(
        rcs_mod,
        "public_destination_payload",
        lambda _r: {"connector_code": "postgres", "config": dict(SINK_CONFIG)},
    )
    return conn


def test_run_connection_sync_google_sheet_to_postgres(mock_gspread, mock_elt_repo) -> None:
    if not _sink_reachable():
        pytest.skip("TEST_SINK PostgreSQL недоступен (порт 5544)")

    summary = run_connection_sync(mock_elt_repo, workspace_id=1, domain_connection_id=1)

    assert summary["total_rows_written"] >= 1
    assert summary["source_connector"] == "google_sheet"
    assert summary["destination_connector"] == "postgres"
    streams = summary.get("streams") or []
    assert any(s.get("stream_name") == "orders" and s.get("rows_written", 0) >= 1 for s in streams)

    from datanorma.destinations.postgres import _normalize_postgres_url

    eng = create_engine(_normalize_postgres_url(SINK_CONFIG["url"]))
    with eng.connect() as c:
        cnt = c.execute(
            text(f'SELECT COUNT(*) FROM "{SINK_CONFIG["schema"]}"."{SINK_CONFIG["table"]}" WHERE order_id = :oid'),
            {"oid": "GS-E2E-001"},
        ).scalar()
    assert int(cnt or 0) >= 1
