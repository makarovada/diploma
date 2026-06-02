from __future__ import annotations

import pytest

from datanorma.web.sync_launch import build_sync_audit_payload

pytestmark = pytest.mark.unit


def test_build_sync_audit_payload_minimal() -> None:
    payload = build_sync_audit_payload(execution_mode="dagster")
    assert payload == {"execution_mode": "dagster"}


def test_build_sync_audit_payload_full() -> None:
    payload = build_sync_audit_payload(
        execution_mode="inline_fallback",
        integration_code="ozon",
        stream_name="orders",
        domain_connection_id=7,
        connection_id=11,
        retry_of=3,
        dagster_run_id="dag-42",
        dagster_error="dagster down",
        error="inline failed",
        elt_summary={"total_rows_written": 10},
    )
    assert payload == {
        "execution_mode": "inline_fallback",
        "integration_code": "ozon",
        "stream_name": "orders",
        "domain_connection_id": 7,
        "connection_id": 11,
        "retry_of": 3,
        "dagster_run_id": "dag-42",
        "dagster_error": "dagster down",
        "error": "inline failed",
        "elt_summary": {"total_rows_written": 10},
    }

