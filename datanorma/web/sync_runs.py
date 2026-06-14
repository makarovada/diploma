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

_SYNC_RUN_COLS = (
    "id, workspace_id, connection_id, domain_connection_id, integration_code, stream_name, status, "
    "dagster_run_id, started_at, finished_at, triggered_by, error_message, created_at, updated_at, meta"
)

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


class SyncCancelled(Exception):
    """Inline-синк прерван по запросу отмены (частичный summary в .summary)."""

    def __init__(self, summary: dict[str, Any]):
        self.summary = summary
        super().__init__("sync cancelled")


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


def _parse_sync_run_meta(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def public_sync_run_row(row: dict[str, Any]) -> dict[str, Any]:
    """Обогатить sync_run для API: записи, проблемы, длительность из meta."""
    out = dict(row)
    meta = _parse_sync_run_meta(out.get("meta"))
    summary = meta.get("elt_summary") if isinstance(meta.get("elt_summary"), dict) else {}
    out["records_written"] = int(summary.get("total_rows_written") or 0)
    out["issues_count"] = int(summary.get("total_issues") or 0)

    duration_ms = meta.get("duration_ms")
    if duration_ms is not None:
        try:
            out["duration_ms"] = max(0, int(duration_ms))
        except (TypeError, ValueError):
            pass
    elif out.get("started_at") and out.get("finished_at"):
        try:
            started = out["started_at"]
            finished = out["finished_at"]
            if hasattr(started, "timestamp") and hasattr(finished, "timestamp"):
                out["duration_ms"] = max(0, int((finished - started).total_seconds() * 1000))
        except Exception:
            pass
    return out


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
    domain_connection_id: int | None = None,
    workspace_id: int | None = None,
) -> dict[str, Any]:
    row = conn.execute(
        text(
            "INSERT INTO sync_run (workspace_id, connection_id, domain_connection_id, integration_code, stream_name, status, triggered_by, meta, created_at, updated_at) "
            "VALUES (:wid, :cid, :dcid, :ic, :sn, 'queued', :tb, CAST(:meta AS jsonb), NOW(), NOW()) "
            f"RETURNING {_SYNC_RUN_COLS}"
        ),
        {
            "wid": workspace_id,
            "cid": connection_id,
            "dcid": domain_connection_id,
            "ic": integration_code,
            "sn": stream_name,
            "tb": triggered_by,
            "meta": json.dumps({"note": note or ""}, ensure_ascii=False),
        },
    ).mappings().one()
    return public_sync_run_row(dict(row))


def mark_sync_run_running(conn: Connection, run_id: int, dagster_run_id: str) -> dict[str, Any]:
    row = conn.execute(
        text(
            "UPDATE sync_run SET status = 'running', dagster_run_id = :drid, "
            "started_at = COALESCE(started_at, clock_timestamp()), "
            "updated_at = clock_timestamp(), error_message = NULL WHERE id = :id "
            f"RETURNING {_SYNC_RUN_COLS}"
        ),
        {"id": run_id, "drid": dagster_run_id},
    ).mappings().one()
    return public_sync_run_row(dict(row))


def mark_sync_run_failed(conn: Connection, run_id: int, message: str) -> dict[str, Any]:
    row = conn.execute(
        text(
            "UPDATE sync_run SET status = 'failed', finished_at = COALESCE(finished_at, clock_timestamp()), "
            "updated_at = clock_timestamp(), error_message = :msg WHERE id = :id "
            f"RETURNING {_SYNC_RUN_COLS}"
        ),
        {"id": run_id, "msg": message[:3000]},
    ).mappings().one()
    return public_sync_run_row(dict(row))


def mark_sync_run_success(
    conn: Connection,
    run_id: int,
    *,
    meta_patch: dict[str, Any] | None = None,
) -> dict[str, Any]:
    mp = json.dumps(meta_patch or {}, ensure_ascii=False)
    row = conn.execute(
        text(
            "UPDATE sync_run SET status = 'success', finished_at = COALESCE(finished_at, clock_timestamp()), "
            "updated_at = clock_timestamp(), error_message = NULL, "
            "meta = COALESCE(meta, '{}'::jsonb) || CAST(:mp AS jsonb), "
            "dagster_run_id = COALESCE(dagster_run_id, 'elt_inline') "
            "WHERE id = :id "
            f"RETURNING {_SYNC_RUN_COLS}"
        ),
        {"id": run_id, "mp": mp},
    ).mappings().one()
    return public_sync_run_row(dict(row))


def mark_sync_run_started_inline(conn: Connection, run_id: int) -> dict[str, Any]:
    """Запуск без Dagster (локальный ELT)."""
    row = conn.execute(
        text(
            "UPDATE sync_run SET status = 'running', started_at = COALESCE(started_at, clock_timestamp()), "
            "updated_at = clock_timestamp(), dagster_run_id = 'elt_inline', error_message = NULL WHERE id = :id "
            f"RETURNING {_SYNC_RUN_COLS}"
        ),
        {"id": run_id},
    ).mappings().one()
    return public_sync_run_row(dict(row))


def resolve_connection(
    conn: Connection,
    *,
    domain_connection_id: int | None = None,
    connection_id: int | None = None,
    integration_code: str | None = None,
    stream_name: str | None = None,
    workspace_id: int | None = None,
) -> tuple[int | None, int | None, str | None, str | None]:
    """sync_state.id, domain connection.id, integration_code, stream_name."""
    if domain_connection_id is not None:
        ws_clause = " AND c.workspace_id = :wid" if workspace_id is not None else ""
        row = conn.execute(
            text(
                "SELECT ss.id AS sync_id, s.connector_code AS ic, cs.stream_name AS sn, c.id AS dcid "
                "FROM connection c "
                "JOIN source s ON s.id = c.source_id "
                "JOIN connection_stream cs ON cs.connection_id = c.id "
                "LEFT JOIN sync_state ss ON ss.connection_stream_id = cs.id "
                "WHERE c.id = :cid AND cs.is_enabled IS TRUE "
                f"{ws_clause} "
                "ORDER BY cs.stream_name "
                "LIMIT 1"
            ),
            {"cid": domain_connection_id, "wid": workspace_id},
        ).mappings().first()
        if row is None:
            raise SyncRunError("domain connection has no enabled streams")
        sid = row["sync_id"]
        if sid is None:
            raise SyncRunError("stream is not linked to sync_state")
        return int(sid), int(row["dcid"]), str(row["ic"]), str(row["sn"])

    if connection_id is not None:
        ws_clause = " AND ss.workspace_id = :wid" if workspace_id is not None else ""
        row = conn.execute(
            text(
                "SELECT ss.id, ss.integration_code, ss.stream_name, cs.connection_id AS domain_cid "
                "FROM sync_state ss "
                "LEFT JOIN connection_stream cs ON cs.id = ss.connection_stream_id "
                "WHERE ss.id = :id"
                f"{ws_clause}"
            ),
            {"id": connection_id, "wid": workspace_id},
        ).mappings().first()
        if row is None:
            raise SyncRunError("connection_id not found")
        dc = row["domain_cid"]
        return (
            int(row["id"]),
            int(dc) if dc is not None else None,
            str(row["integration_code"]),
            str(row["stream_name"]),
        )
    if integration_code and stream_name:
        ws_clause = " AND ss.workspace_id = :wid" if workspace_id is not None else ""
        row = conn.execute(
            text(
                "SELECT ss.id, ss.integration_code, ss.stream_name, cs.connection_id AS domain_cid "
                "FROM sync_state ss "
                "LEFT JOIN connection_stream cs ON cs.id = ss.connection_stream_id "
                "WHERE ss.integration_code = :ic AND ss.stream_name = :sn"
                f"{ws_clause}"
            ),
            {"ic": integration_code, "sn": stream_name, "wid": workspace_id},
        ).mappings().first()
        if row is None:
            raise SyncRunError("connection not found by integration_code/stream_name")
        dc = row["domain_cid"]
        return (
            int(row["id"]),
            int(dc) if dc is not None else None,
            str(row["integration_code"]),
            str(row["stream_name"]),
        )
    return None, None, integration_code, stream_name


def attach_load_destination(conn: Connection, row: dict[str, Any]) -> dict[str, Any]:
    """Добавляет в ответ sync_run сведения о приёмнике (через domain connection)."""
    out = public_sync_run_row(dict(row))
    dcid = out.get("domain_connection_id")
    if dcid is None:
        return out
    r = conn.execute(
        text(
            "SELECT d.connector_code, d.name "
            "FROM connection c JOIN destination d ON d.id = c.destination_id "
            "WHERE c.id = :cid"
        ),
        {"cid": int(dcid)},
    ).mappings().first()
    if r:
        out["load_destination"] = {
            "connector_code": str(r["connector_code"]),
            "name": str(r["name"]),
        }
    return out


def list_sync_runs(conn: Connection, limit: int = 50, workspace_id: int | None = None) -> list[dict[str, Any]]:
    lim = max(1, min(limit, 500))
    ws_clause = "WHERE workspace_id = :wid " if workspace_id is not None else ""
    rows = conn.execute(
        text(
            f"SELECT {_SYNC_RUN_COLS} FROM sync_run "
            f"{ws_clause}"
            "ORDER BY id DESC LIMIT :lim"
        ),
        {"lim": lim, "wid": workspace_id},
    ).mappings().all()
    return [public_sync_run_row(dict(r)) for r in rows]


def get_sync_run(conn: Connection, run_id: int, workspace_id: int | None = None) -> dict[str, Any] | None:
    ws_clause = " AND workspace_id = :wid" if workspace_id is not None else ""
    row = conn.execute(
        text(
            f"SELECT {_SYNC_RUN_COLS} FROM sync_run WHERE id = :id"
            f"{ws_clause}"
        ),
        {"id": run_id, "wid": workspace_id},
    ).mappings().first()
    return public_sync_run_row(dict(row)) if row else None


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
                "UPDATE sync_run SET status = :st, finished_at = COALESCE(:fa, finished_at, clock_timestamp()), "
                "updated_at = clock_timestamp() WHERE id = :id "
                f"RETURNING {_SYNC_RUN_COLS}"
            ),
            {"id": run["id"], "st": status, "fa": finished_at},
        ).mappings().one()
        return public_sync_run_row(dict(row))
    row = conn.execute(
        text(
            "UPDATE sync_run SET status = :st, updated_at = clock_timestamp() WHERE id = :id "
            f"RETURNING {_SYNC_RUN_COLS}"
        ),
        {"id": run["id"], "st": status},
    ).mappings().one()
    return public_sync_run_row(dict(row))


def refresh_recent_sync_runs(conn: Connection, limit: int = 50, workspace_id: int | None = None) -> list[dict[str, Any]]:
    runs = list_sync_runs(conn, limit=limit, workspace_id=workspace_id)
    return [refresh_sync_run_status(conn, r) for r in runs]


def is_sync_run_cancel_requested(conn: Connection, run_id: int) -> bool:
    row = conn.execute(
        text("SELECT meta FROM sync_run WHERE id = :id"),
        {"id": run_id},
    ).mappings().first()
    if row is None:
        return False
    meta = _parse_sync_run_meta(row.get("meta"))
    return bool(meta.get("cancel_requested"))


def terminate_dagster_run(dagster_run_id: str) -> None:
    mutation = """
    mutation TerminateRun($runId: String!) {
      terminatePipelineExecution(runId: $runId) {
        __typename
        ... on TerminateRunSuccess {
          run { runId status }
        }
        ... on TerminateRunFailure {
          message
        }
        ... on RunNotFoundError {
          runId
        }
      }
    }
    """
    result = _run_graphql(mutation, {"runId": dagster_run_id}).get("terminatePipelineExecution") or {}
    kind = result.get("__typename")
    if kind == "TerminateRunFailure":
        raise SyncRunError(str(result.get("message") or "Dagster terminate failed"))
    if kind == "RunNotFoundError":
        raise SyncRunError(f"Dagster run not found: {dagster_run_id}")


def request_sync_run_cancel(conn: Connection, run_id: int) -> dict[str, Any]:
    row = conn.execute(
        text(f"SELECT id, status, dagster_run_id FROM sync_run WHERE id = :id"),
        {"id": run_id},
    ).mappings().first()
    if row is None:
        raise SyncRunError("sync run not found")
    status = str(row["status"]).lower()
    if status not in RUNNING_STATUSES:
        raise SyncRunError("sync run is not running")
    drid = row.get("dagster_run_id")
    if drid and str(drid) not in ("", "elt_inline"):
        terminate_dagster_run(str(drid))
    mp = json.dumps({"cancel_requested": True}, ensure_ascii=False)
    updated = conn.execute(
        text(
            "UPDATE sync_run SET meta = COALESCE(meta, '{}'::jsonb) || CAST(:mp AS jsonb), "
            "updated_at = clock_timestamp() WHERE id = :id "
            f"RETURNING {_SYNC_RUN_COLS}"
        ),
        {"id": run_id, "mp": mp},
    ).mappings().one()
    return public_sync_run_row(dict(updated))


def mark_sync_run_cancelled(
    conn: Connection,
    run_id: int,
    *,
    meta_patch: dict[str, Any] | None = None,
) -> dict[str, Any]:
    mp = json.dumps(meta_patch or {}, ensure_ascii=False)
    row = conn.execute(
        text(
            "UPDATE sync_run SET status = 'cancelled', finished_at = COALESCE(finished_at, clock_timestamp()), "
            "updated_at = clock_timestamp(), "
            "meta = COALESCE(meta, '{}'::jsonb) || CAST(:mp AS jsonb) "
            "WHERE id = :id "
            f"RETURNING {_SYNC_RUN_COLS}"
        ),
        {"id": run_id, "mp": mp},
    ).mappings().one()
    return public_sync_run_row(dict(row))
