from __future__ import annotations

import time
from typing import Any

from sqlalchemy.engine import Connection

from datanorma.elt.run_connection_sync import run_connection_sync
from datanorma.web.sync_runs import (
    SyncRunError,
    launch_dagster_run,
    mark_sync_run_running,
    mark_sync_run_started_inline,
    mark_sync_run_success,
)


def build_sync_audit_payload(
    *,
    execution_mode: str,
    integration_code: str | None = None,
    stream_name: str | None = None,
    domain_connection_id: int | None = None,
    connection_id: int | None = None,
    retry_of: int | None = None,
    dagster_run_id: str | None = None,
    dagster_error: str | None = None,
    error: str | None = None,
    elt_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"execution_mode": execution_mode}
    if integration_code is not None:
        payload["integration_code"] = integration_code
    if stream_name is not None:
        payload["stream_name"] = stream_name
    if domain_connection_id is not None:
        payload["domain_connection_id"] = domain_connection_id
    if connection_id is not None:
        payload["connection_id"] = connection_id
    if retry_of is not None:
        payload["retry_of"] = retry_of
    if dagster_run_id is not None:
        payload["dagster_run_id"] = dagster_run_id
    if dagster_error is not None:
        payload["dagster_error"] = dagster_error
    if error is not None:
        payload["error"] = error
    if elt_summary is not None:
        payload["elt_summary"] = elt_summary
    return payload


def launch_sync_run_via_dagster(
    *,
    conn: Connection,
    run_id: int,
    integration_code: str | None,
    stream_name: str | None,
    triggered_by: str,
) -> dict[str, Any]:
    launch = launch_dagster_run(
        sync_run_id=run_id,
        integration_code=integration_code,
        stream_name=stream_name,
        triggered_by=triggered_by,
    )
    return mark_sync_run_running(conn, run_id=run_id, dagster_run_id=launch.run_id)


def run_sync_inline_fallback(
    *,
    conn: Connection,
    run_id: int,
    workspace_id: int,
    domain_connection_id: int,
    dagster_error: Exception,
    extra_meta: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    mark_sync_run_started_inline(conn, run_id=run_id)
    t0 = time.monotonic()
    summary = run_connection_sync(
        conn,
        workspace_id=workspace_id,
        domain_connection_id=domain_connection_id,
        sync_run_id=run_id,
    )
    duration_ms = max(1, int((time.monotonic() - t0) * 1000))
    meta_patch = {
        "elt_summary": summary,
        "duration_ms": duration_ms,
        "execution_mode": "inline_fallback",
        "dagster_error": str(dagster_error),
    }
    if extra_meta:
        meta_patch.update(extra_meta)
    row = mark_sync_run_success(conn, run_id, meta_patch=meta_patch)
    return row, summary

