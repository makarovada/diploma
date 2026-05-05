"""Запись и выборка audit_log (отдельная транзакция для событий при rollback основного запроса)."""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import IntegrityError, ProgrammingError

logger = logging.getLogger(__name__)


def _insert_audit_row(
    engine: Engine,
    *,
    workspace_id: int | None,
    actor_user_id: int | None,
    action: str,
    resource_type: str | None,
    resource_id: str | None,
    result: str,
    payload: dict[str, Any] | None,
    ip_address: str | None,
    user_agent: str | None,
) -> None:
    with engine.begin() as c:
        c.execute(
            text(
                "INSERT INTO audit_log (workspace_id, actor_user_id, action, resource_type, resource_id, "
                "result, payload_json, ip_address, user_agent) "
                "VALUES (:wid, :aid, :act, :rtype, :rid, :res, CAST(:payload AS jsonb), :ip, :ua)"
            ),
            {
                "wid": workspace_id,
                "aid": actor_user_id,
                "act": action[:128],
                "rtype": resource_type[:64] if resource_type else None,
                "rid": resource_id[:128] if resource_id else None,
                "res": result[:32],
                "payload": json.dumps(payload, ensure_ascii=False) if payload is not None else None,
                "ip": ip_address[:64] if ip_address else None,
                "ua": user_agent,
            },
        )


def record_audit_event(
    engine: Engine,
    *,
    workspace_id: int | None,
    actor_user_id: int | None,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    result: str = "success",
    payload: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Фиксирует событие в отдельной транзакции (commit при выходе из контекста)."""
    common = dict(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        result=result,
        payload=payload,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    try:
        _insert_audit_row(
            engine,
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            **common,
        )
    except ProgrammingError as exc:
        msg = str(exc).lower()
        if "audit_log" in msg and ("does not exist" in msg or "undefinedtable" in msg):
            logger.debug("audit_log missing; skip audit write (%s)", action)
            return
        raise
    except IntegrityError:
        if workspace_id is None and actor_user_id is None:
            raise
        merged = dict(common)
        if payload is not None:
            p = dict(payload)
            if workspace_id is not None:
                p["workspace_id_unresolved"] = workspace_id
            if actor_user_id is not None:
                p["actor_user_id_unresolved"] = actor_user_id
            merged["payload"] = p
        else:
            extra: dict[str, Any] = {}
            if workspace_id is not None:
                extra["workspace_id_unresolved"] = workspace_id
            if actor_user_id is not None:
                extra["actor_user_id_unresolved"] = actor_user_id
            merged["payload"] = extra if extra else None
        logger.debug("audit_log FK retry without workspace/actor (%s)", action)
        _insert_audit_row(engine, workspace_id=None, actor_user_id=None, **merged)


def list_audit_log(
    conn: Connection,
    *,
    workspace_id: int | None = None,
    actor_username: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    result: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    lim = max(1, min(limit, 200))
    off = max(0, offset)
    filters: list[str] = ["1=1"]
    params: dict[str, Any] = {"lim": lim, "off": off}
    if workspace_id is not None:
        filters.append("(al.workspace_id = :wid OR al.workspace_id IS NULL)")
        params["wid"] = workspace_id
    if actor_username and actor_username.strip():
        filters.append("u.username ILIKE :actor_like")
        params["actor_like"] = f"%{actor_username.strip()}%"
    if action and action.strip():
        filters.append("al.action = :action")
        params["action"] = action.strip()
    if resource_type and resource_type.strip():
        filters.append("al.resource_type = :rtype")
        params["rtype"] = resource_type.strip()
    if result and result.strip():
        filters.append("al.result = :result")
        params["result"] = result.strip()
    if date_from and date_from.strip():
        filters.append("(al.created_at AT TIME ZONE 'UTC')::date >= CAST(:df AS date)")
        params["df"] = date_from.strip()[:32]
    if date_to and date_to.strip():
        filters.append("(al.created_at AT TIME ZONE 'UTC')::date <= CAST(:dt AS date)")
        params["dt"] = date_to.strip()[:32]
    where_sql = " AND ".join(filters)
    try:
        rows = conn.execute(
            text(
                f"SELECT al.id, al.workspace_id, al.actor_user_id, u.username AS actor_username, "
                f"al.action, al.resource_type, al.resource_id, al.result, al.payload_json, "
                f"al.ip_address, al.user_agent, al.created_at "
                f"FROM audit_log al "
                f"LEFT JOIN app_user u ON u.id = al.actor_user_id "
                f"WHERE {where_sql} "
                f"ORDER BY al.created_at DESC, al.id DESC "
                f"LIMIT :lim OFFSET :off"
            ),
            params,
        ).mappings().all()
    except ProgrammingError as exc:
        msg = str(exc).lower()
        if "audit_log" in msg and ("does not exist" in msg or "undefinedtable" in msg):
            return []
        raise
    out: list[dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        if d.get("created_at") is not None and hasattr(d["created_at"], "isoformat"):
            d["created_at"] = d["created_at"].isoformat()
        out.append(d)
    return out
