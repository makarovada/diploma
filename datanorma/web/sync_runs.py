"""Сервис запуска и отслеживания sync_run через Dagster GraphQL."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from typing import Any
from urllib.parse import urljoin

import httpx
from sqlalchemy import text
from sqlalchemy.engine import Connection

from datanorma.web.config import dagster_console_url

SYNC_RUN_STATUSES = {"queued", "running", "success", "failed", "cancelled"}
TERMINAL_STATUSES = {"success", "failed", "cancelled"}
RUNNING_STATUSES = {"queued", "running"}

_DAGSTER_STATUS_MAP = {
    "QUEUED": "queued",
    "STARTED": "running",
    "STARTING": "running",
    "SUCCESS": "success",
    "FAILURE": "failed",
    "CANCELED": "cancelled",
    "CANCELING": "cancelled",
}


class SyncRunError(RuntimeError):
    """Ошибка запуска/опроса sync run."""


@dataclass(frozen=True)
class DagsterLaunchResult:
    run_id: str
    status: str


def _graphql_url() -> str:
    base = dagster_console_url().rstrip("/") + "/"
    return urljoin(base, "graphql")


def _run_graphql(query: str, variables: dict[str, Any]) -> dict[str, Any]:
    payload = {"query": query, "variables": variables}
    with httpx.Client(timeout=15.0) as client:
        resp = client.post(_graphql_url(), json=payload)
    if resp.status_code >= 400:
        raise SyncRunError(f"Dagster GraphQL HTTP {resp.status_code}")
    data = resp.json()
    if "errors" in data and data["errors"]:
        msg = "; ".join(str(e.get("message", e)) for e in data["errors"])
        raise SyncRunError(f"Dagster GraphQL error: {msg}")
    if "data" not in data:
        raise SyncRunError("Dagster GraphQL returned empty payload")
    return data["data"]


def _discover_job_selector(job_name: str = "daily_refresh") -> dict[str, str]:
    query = """
    query ReposAndJobs {
      repositoriesOrError {
        __typename
        ... on RepositoryConnection {
          nodes {
            name
            location { name }
            jobs { name }
            pipelines { name }
          }
        }
      }
    }
    """
    data = _run_graphql(query, {})
    root = data.get("repositoriesOrError") or {}
    if root.get("__typename") != "RepositoryConnection":
        raise SyncRunError("Dagster repositories are unavailable")
    for node in root.get("nodes") or []:
        jobs = {j.get("name") for j in (node.get("jobs") or [])}
        pipelines = {p.get("name") for p in (node.get("pipelines") or [])}
        if job_name in jobs or job_name in pipelines:
            location = (node.get("location") or {}).get("name")
            repo_name = node.get("name")
            if not location or not repo_name:
                continue
            return {
                "repositoryLocationName": location,
                "repositoryName": repo_name,
                "pipelineName": job_name,
            }
    raise SyncRunError(f"Dagster job '{job_name}' not found")


def launch_dagster_run(
    *,
    sync_run_id: int,
    integration_code: str | None,
    stream_name: str | None,
    triggered_by: str,
    job_name: str = "daily_refresh",
) -> DagsterLaunchResult:
    selector = _discover_job_selector(job_name=job_name)
    mutation = """
    mutation LaunchPipeline($executionParams: ExecutionParams!) {
      launchPipelineExecution(executionParams: $executionParams) {
        __typename
        ... on LaunchRunSuccess {
          run { runId status }
        }
        ... on LaunchPipelineRunSuccess {
          run { runId status }
        }
        ... on PythonError {
          message
        }
        ... on InvalidStepError {
          invalidStepKey
        }
        ... on PipelineNotFoundError {
          message
        }
        ... on RunConfigValidationInvalid {
          errors { message }
        }
      }
    }
    """
    tags = [
        {"key": "sync_run_id", "value": str(sync_run_id)},
        {"key": "triggered_by", "value": triggered_by},
    ]
    if integration_code:
        tags.append({"key": "integration_code", "value": integration_code})
    if stream_name:
        tags.append({"key": "stream_name", "value": stream_name})
    execution_params = {
        "selector": selector,
        "mode": "default",
        "executionMetadata": {"tags": tags},
    }
    result = _run_graphql(mutation, {"executionParams": execution_params}).get("launchPipelineExecution") or {}
    kind = result.get("__typename")
    if kind in {"LaunchPipelineRunSuccess", "LaunchRunSuccess"}:
        run = result.get("run") or {}
        rid = run.get("runId")
        status = _DAGSTER_STATUS_MAP.get((run.get("status") or "").upper(), "running")
        if not rid:
            raise SyncRunError("Dagster launch returned empty run id")
        return DagsterLaunchResult(run_id=rid, status=status)
    if kind == "RunConfigValidationInvalid":
        errors = [e.get("message", "") for e in (result.get("errors") or []) if isinstance(e, dict)]
        raise SyncRunError("Dagster config invalid: " + "; ".join(x for x in errors if x))
    message = result.get("message") or result.get("invalidStepKey") or f"Dagster launch failed ({kind})"
    raise SyncRunError(str(message))


def fetch_dagster_run_status(dagster_run_id: str) -> tuple[str, datetime | None]:
    query = """
    query PipelineRunStatus($runId: ID!) {
      pipelineRunOrError(runId: $runId) {
        __typename
        ... on PipelineRun {
          status
          endTime
        }
      }
    }
    """
    data = _run_graphql(query, {"runId": dagster_run_id}).get("pipelineRunOrError") or {}
    if data.get("__typename") != "PipelineRun":
        raise SyncRunError("Dagster run not found")
    status = _DAGSTER_STATUS_MAP.get((data.get("status") or "").upper(), "running")
    end_ts = data.get("endTime")
    finished_at = datetime.fromtimestamp(end_ts, tz=timezone.utc) if isinstance(end_ts, (int, float)) else None
    return status, finished_at


def create_sync_run(
    conn: Connection,
    *,
    connection_id: int | None,
    integration_code: str | None,
    stream_name: str | None,
    triggered_by: str,
    note: str | None = None,
) -> dict[str, Any]:
    row = conn.execute(
        text(
            "INSERT INTO sync_run (connection_id, integration_code, stream_name, status, triggered_by, meta, created_at, updated_at) "
            "VALUES (:cid, :ic, :sn, 'queued', :tb, CAST(:meta AS jsonb), NOW(), NOW()) "
            "RETURNING id, connection_id, integration_code, stream_name, status, dagster_run_id, "
            "started_at, finished_at, triggered_by, error_message, created_at, updated_at"
        ),
        {
            "cid": connection_id,
            "ic": integration_code,
            "sn": stream_name,
            "tb": triggered_by,
            "meta": json.dumps({"note": note or ""}, ensure_ascii=False),
        },
    ).mappings().one()
    return dict(row)


def mark_sync_run_running(conn: Connection, run_id: int, dagster_run_id: str) -> dict[str, Any]:
    row = conn.execute(
        text(
            "UPDATE sync_run SET status = 'running', dagster_run_id = :drid, started_at = COALESCE(started_at, NOW()), "
            "updated_at = NOW(), error_message = NULL WHERE id = :id "
            "RETURNING id, connection_id, integration_code, stream_name, status, dagster_run_id, "
            "started_at, finished_at, triggered_by, error_message, created_at, updated_at"
        ),
        {"id": run_id, "drid": dagster_run_id},
    ).mappings().one()
    return dict(row)


def mark_sync_run_failed(conn: Connection, run_id: int, message: str) -> dict[str, Any]:
    row = conn.execute(
        text(
            "UPDATE sync_run SET status = 'failed', finished_at = COALESCE(finished_at, NOW()), "
            "updated_at = NOW(), error_message = :msg WHERE id = :id "
            "RETURNING id, connection_id, integration_code, stream_name, status, dagster_run_id, "
            "started_at, finished_at, triggered_by, error_message, created_at, updated_at"
        ),
        {"id": run_id, "msg": message[:3000]},
    ).mappings().one()
    return dict(row)


def resolve_connection(
    conn: Connection,
    *,
    connection_id: int | None,
    integration_code: str | None,
    stream_name: str | None,
) -> tuple[int | None, str | None, str | None]:
    if connection_id is not None:
        row = conn.execute(
            text("SELECT id, integration_code, stream_name FROM sync_state WHERE id = :id"),
            {"id": connection_id},
        ).mappings().first()
        if row is None:
            raise SyncRunError("connection_id not found")
        return int(row["id"]), str(row["integration_code"]), str(row["stream_name"])
    if integration_code and stream_name:
        row = conn.execute(
            text(
                "SELECT id, integration_code, stream_name FROM sync_state "
                "WHERE integration_code = :ic AND stream_name = :sn"
            ),
            {"ic": integration_code, "sn": stream_name},
        ).mappings().first()
        if row is None:
            raise SyncRunError("connection not found by integration_code/stream_name")
        return int(row["id"]), str(row["integration_code"]), str(row["stream_name"])
    return None, integration_code, stream_name


def list_sync_runs(conn: Connection, limit: int = 50) -> list[dict[str, Any]]:
    lim = max(1, min(limit, 500))
    rows = conn.execute(
        text(
            "SELECT id, connection_id, integration_code, stream_name, status, dagster_run_id, "
            "started_at, finished_at, triggered_by, error_message, created_at, updated_at "
            "FROM sync_run ORDER BY id DESC LIMIT :lim"
        ),
        {"lim": lim},
    ).mappings().all()
    return [dict(r) for r in rows]


def get_sync_run(conn: Connection, run_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        text(
            "SELECT id, connection_id, integration_code, stream_name, status, dagster_run_id, "
            "started_at, finished_at, triggered_by, error_message, created_at, updated_at "
            "FROM sync_run WHERE id = :id"
        ),
        {"id": run_id},
    ).mappings().first()
    return dict(row) if row else None


def refresh_sync_run_status(conn: Connection, run: dict[str, Any]) -> dict[str, Any]:
    if run.get("status") not in RUNNING_STATUSES:
        return run
    dagster_run_id = run.get("dagster_run_id")
    if not dagster_run_id:
        return run
    try:
        status, finished_at = fetch_dagster_run_status(str(dagster_run_id))
    except SyncRunError:
        return run
    if status == run.get("status"):
        return run
    if status in TERMINAL_STATUSES:
        row = conn.execute(
            text(
                "UPDATE sync_run SET status = :st, finished_at = COALESCE(:fa, finished_at, NOW()), "
                "updated_at = NOW() WHERE id = :id "
                "RETURNING id, connection_id, integration_code, stream_name, status, dagster_run_id, "
                "started_at, finished_at, triggered_by, error_message, created_at, updated_at"
            ),
            {"id": run["id"], "st": status, "fa": finished_at},
        ).mappings().one()
        return dict(row)
    row = conn.execute(
        text(
            "UPDATE sync_run SET status = :st, updated_at = NOW() WHERE id = :id "
            "RETURNING id, connection_id, integration_code, stream_name, status, dagster_run_id, "
            "started_at, finished_at, triggered_by, error_message, created_at, updated_at"
        ),
        {"id": run["id"], "st": status},
    ).mappings().one()
    return dict(row)


def refresh_recent_sync_runs(conn: Connection, limit: int = 50) -> list[dict[str, Any]]:
    runs = list_sync_runs(conn, limit=limit)
    return [refresh_sync_run_status(conn, r) for r in runs]
