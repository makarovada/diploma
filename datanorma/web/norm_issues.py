"""Чтение normalization_issue (ELT-схема после миграции 016)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection, RowMapping

_NORM_ISSUE_SELECT = """
SELECT
    ni.id,
    ni.sync_run_id,
    ni.connection_id,
    ni.stream_name,
    ni.source_record_id,
    ni.target_field,
    ni.error_code,
    ni.error_text,
    ni.raw_value,
    ni.created_at,
    COALESCE(ni.status, 'open') AS status,
    ni.resolved_at,
    ni.resolution_note,
    ni.resolved_by,
    sr.integration_code AS source_system,
    c.name AS connection_name
FROM normalization_issue ni
LEFT JOIN sync_run sr ON sr.id = ni.sync_run_id
LEFT JOIN connection c ON c.id = ni.connection_id
"""


def _public_row(row: RowMapping | dict[str, Any]) -> dict[str, Any]:
    """Единый DTO для React (совместим с legacy field_name / issue_type)."""
    d = dict(row)
    target = d.get("target_field")
    err_code = d.get("error_code") or "cast_error"
    err_text = d.get("error_text")
    raw = d.get("raw_value")
    original = err_text
    if raw is not None and str(raw).strip():
        original = f"{err_text or ''} (raw: {raw})".strip()
    return {
        "id": d.get("id"),
        "sync_run_id": d.get("sync_run_id"),
        "connection_id": d.get("connection_id"),
        "stream_name": d.get("stream_name"),
        "batch_id": d.get("stream_name"),
        "source_system": d.get("source_system"),
        "connection_name": d.get("connection_name"),
        "source_record_id": d.get("source_record_id"),
        "field_name": target,
        "target_field": target,
        "issue_type": err_code,
        "error_code": err_code,
        "message": err_text,
        "error_text": err_text,
        "raw_value": raw,
        "status": d.get("status") or "open",
        "resolved_at": d.get("resolved_at"),
        "resolution_note": d.get("resolution_note"),
        "resolved_by": d.get("resolved_by"),
        "created_at": d.get("created_at"),
    }


def list_norm_issues_for_run(conn: Connection, *, sync_run_id: int, limit: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        text(
            _NORM_ISSUE_SELECT
            + " WHERE ni.sync_run_id = :rid ORDER BY ni.id ASC LIMIT :lim"
        ),
        {"rid": sync_run_id, "lim": limit},
    ).mappings().all()
    return [_public_row(r) for r in rows]


def list_norm_issues_for_workspace(
    conn: Connection,
    *,
    workspace_id: int,
    limit: int,
    integration_code: str | None = None,
) -> list[dict[str, Any]]:
    filt = "sr.workspace_id = :wid"
    params: dict[str, Any] = {"wid": workspace_id, "lim": limit}
    if integration_code:
        filt += " AND sr.integration_code = :ic"
        params["ic"] = integration_code
    rows = conn.execute(
        text(_NORM_ISSUE_SELECT + f" WHERE {filt} ORDER BY ni.created_at DESC, ni.id DESC LIMIT :lim"),
        params,
    ).mappings().all()
    return [_public_row(r) for r in rows]
