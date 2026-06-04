"""Запуск ELT-синхронизаций по cron расписанию connection (общая логика для Dagster sensor и FastAPI)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

from datanorma.config import get_settings
from datanorma.web.sync_launch import run_sync_inline_for_connection
from datanorma.web.sync_runs import (
    create_sync_run,
    mark_sync_run_failed,
)

_log = logging.getLogger(__name__)


def cron_fires_at_local_minute(schedule: str, tz_name: str, now_utc: datetime) -> bool:
    from croniter import croniter

    expr = (schedule or "").strip()
    if not expr:
        return False
    try:
        tz = ZoneInfo((tz_name or "UTC").strip() or "UTC")
    except ZoneInfoNotFoundError:
        tz = timezone.utc
    local = now_utc.astimezone(tz).replace(second=0, microsecond=0)
    base_naive = (local - timedelta(seconds=30)).replace(tzinfo=None)
    itr = croniter(expr, base_naive)
    nxt_naive = itr.get_next(datetime)
    nxt = nxt_naive.replace(tzinfo=tz)
    return nxt == local


def slot_key_for(cron: str, tz_name: str, now_utc: datetime) -> str | None:
    if not cron_fires_at_local_minute(cron, tz_name, now_utc):
        return None
    try:
        z = ZoneInfo((tz_name or "UTC").strip() or "UTC")
    except ZoneInfoNotFoundError:
        z = timezone.utc
    local_min = now_utc.astimezone(z).replace(second=0, microsecond=0)
    return f"{local_min.isoformat()}|{tz_name or 'UTC'}"


def next_scheduled_run_utc(
    schedule: str,
    tz_name: str,
    *,
    now_utc: datetime | None = None,
) -> datetime | None:
    """Следующий запуск cron в UTC (для UI расписаний)."""
    from croniter import croniter

    expr = (schedule or "").strip()
    if not expr:
        return None
    now_utc = now_utc or datetime.now(timezone.utc)
    try:
        tz = ZoneInfo((tz_name or "UTC").strip() or "UTC")
    except ZoneInfoNotFoundError:
        tz = timezone.utc
    local = now_utc.astimezone(tz)
    base_naive = local.replace(tzinfo=None)
    try:
        itr = croniter(expr, base_naive)
        nxt_naive = itr.get_next(datetime)
    except (ValueError, KeyError):
        return None
    return nxt_naive.replace(tzinfo=tz).astimezone(timezone.utc)


def list_scheduled_connections(conn: Connection) -> list[dict[str, object]]:
    return (
        conn.execute(
            text(
                "SELECT c.id, c.workspace_id, s.connector_code AS integration_code, "
                "c.schedule_cron, c.timezone "
                "FROM connection c "
                "JOIN source s ON s.id = c.source_id AND s.workspace_id = c.workspace_id "
                "WHERE c.is_active IS TRUE "
                "AND c.schedule_cron IS NOT NULL AND TRIM(c.schedule_cron) <> ''"
            )
        )
        .mappings()
        .all()
    )


def schedule_slot_already_fired(conn: Connection, *, domain_connection_id: int, slot_key: str) -> bool:
    row = conn.execute(
        text(
            "SELECT 1 FROM sync_run "
            "WHERE domain_connection_id = :dcid AND triggered_by = 'schedule' "
            "AND meta->>'schedule_slot' = :slot LIMIT 1"
        ),
        {"dcid": domain_connection_id, "slot": slot_key},
    ).first()
    return row is not None


def run_scheduled_sync(
    conn: Connection,
    *,
    workspace_id: int,
    domain_connection_id: int,
    integration_code: str,
    slot_key: str,
) -> None:
    row = create_sync_run(
        conn,
        connection_id=None,
        domain_connection_id=domain_connection_id,
        integration_code=integration_code,
        stream_name="*",
        triggered_by="schedule",
        note=None,
        workspace_id=workspace_id,
    )
    run_id = int(row["id"])
    conn.execute(
        text("UPDATE sync_run SET meta = CAST(:meta AS jsonb) WHERE id = :id"),
        {
            "id": run_id,
            "meta": json.dumps({"schedule_slot": slot_key}, ensure_ascii=False),
        },
    )
    try:
        run_sync_inline_for_connection(
            conn=conn,
            run_id=run_id,
            workspace_id=workspace_id,
            domain_connection_id=domain_connection_id,
            extra_meta={"schedule_slot": slot_key},
        )
        conn.execute(
            text(
                "UPDATE sync_run SET meta = COALESCE(meta, '{}'::jsonb) || CAST(:meta AS jsonb) WHERE id = :id"
            ),
            {
                "id": run_id,
                "meta": json.dumps(
                    {"schedule_slot": slot_key, "execution_mode": "inline"},
                    ensure_ascii=False,
                ),
            },
        )
    except Exception as exc:
        mark_sync_run_failed(conn, run_id=run_id, message=str(exc))
        _log.exception(
            "Scheduled ELT sync failed connection_id=%s run_id=%s",
            domain_connection_id,
            run_id,
        )
        raise


def collect_due_connections(
    conn: Connection,
    *,
    now_utc: datetime,
    fired: dict[str, str] | None = None,
) -> list[tuple[int, int, str, str]]:
    """Вернуть (connection_id, workspace_id, integration_code, slot_key) для запуска."""
    due: list[tuple[int, int, str, str]] = []
    cursor = fired or {}
    for r in list_scheduled_connections(conn):
        cid = int(r["id"])
        wid = int(r["workspace_id"])
        ic = str(r["integration_code"] or "").strip()
        cron = str(r["schedule_cron"] or "")
        tz = str(r["timezone"] or "UTC")
        slot = slot_key_for(cron, tz, now_utc)
        if slot is None:
            continue
        if cursor.get(str(cid)) == slot:
            continue
        if schedule_slot_already_fired(conn, domain_connection_id=cid, slot_key=slot):
            continue
        due.append((cid, wid, ic, slot))
    return due


def run_due_scheduled_syncs(
    engine: Engine,
    *,
    now_utc: datetime | None = None,
    fired: dict[str, str] | None = None,
) -> tuple[int, list[str], dict[str, str]]:
    """Запустить все due-синхронизации. Возвращает (count, errors, updated_fired)."""
    now = now_utc or datetime.now(timezone.utc)
    cursor = dict(fired or {})
    errors: list[str] = []

    with engine.connect() as conn:
        due = collect_due_connections(conn, now_utc=now, fired=cursor)

    if not due:
        return 0, [], cursor

    for cid, wid, ic, slot in due:
        cursor[str(cid)] = slot
        try:
            with engine.begin() as conn:
                run_scheduled_sync(
                    conn,
                    workspace_id=wid,
                    domain_connection_id=cid,
                    integration_code=ic,
                    slot_key=slot,
                )
        except Exception as exc:
            errors.append(f"connection {cid}: {exc}")

    return len(due), errors, cursor
