"""CRUD и утилиты для доменных сущностей source / destination / connection (Фаза 4)."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection


class EltRepoError(RuntimeError):
    pass


def _config_load(raw: str | None) -> dict[str, Any]:
    if not raw or not raw.strip():
        return {}
    try:
        v = json.loads(raw)
        return v if isinstance(v, dict) else {}
    except json.JSONDecodeError:
        return {}


def _config_dump(cfg: dict[str, Any] | None) -> str:
    if not cfg:
        return "{}"
    return json.dumps(cfg, ensure_ascii=False)


def list_sources(conn: Connection, *, workspace_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        text(
            "SELECT id, workspace_id, name, connector_code, config_encrypted, status, created_by, "
            "created_at, updated_at, last_checked_at FROM source WHERE workspace_id = :wid ORDER BY id"
        ),
        {"wid": workspace_id},
    ).mappings().all()
    return [dict(r) for r in rows]


def get_source(conn: Connection, *, workspace_id: int, source_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        text(
            "SELECT id, workspace_id, name, connector_code, config_encrypted, status, created_by, "
            "created_at, updated_at, last_checked_at FROM source WHERE id = :id AND workspace_id = :wid"
        ),
        {"id": source_id, "wid": workspace_id},
    ).mappings().first()
    return dict(row) if row else None


def create_source_row(
    conn: Connection,
    *,
    workspace_id: int,
    name: str,
    connector_code: str,
    config: dict[str, Any],
    created_by: str | None,
) -> dict[str, Any]:
    row = conn.execute(
        text(
            "INSERT INTO source (workspace_id, name, connector_code, config_encrypted, status, created_by, created_at, updated_at) "
            "VALUES (:wid, :name, :cc, :cfg, 'active', :cb, NOW(), NOW()) "
            "RETURNING id, workspace_id, name, connector_code, config_encrypted, status, created_by, "
            "created_at, updated_at, last_checked_at"
        ),
        {
            "wid": workspace_id,
            "name": name.strip(),
            "cc": connector_code.strip(),
            "cfg": _config_dump(config),
            "cb": created_by,
        },
    ).mappings().one()
    return dict(row)


def update_source_row(
    conn: Connection,
    *,
    workspace_id: int,
    source_id: int,
    name: str | None = None,
    connector_code: str | None = None,
    config: dict[str, Any] | None = None,
    status: str | None = None,
) -> dict[str, Any] | None:
    cur = get_source(conn, workspace_id=workspace_id, source_id=source_id)
    if cur is None:
        return None
    new_name = name.strip() if name is not None else cur["name"]
    new_cc = connector_code.strip() if connector_code is not None else cur["connector_code"]
    new_cfg = _config_dump(config) if config is not None else cur["config_encrypted"]
    new_st = status.strip() if status is not None else cur["status"]
    row = conn.execute(
        text(
            "UPDATE source SET name = :name, connector_code = :cc, config_encrypted = :cfg, status = :st, updated_at = NOW() "
            "WHERE id = :id AND workspace_id = :wid "
            "RETURNING id, workspace_id, name, connector_code, config_encrypted, status, created_by, "
            "created_at, updated_at, last_checked_at"
        ),
        {"id": source_id, "wid": workspace_id, "name": new_name, "cc": new_cc, "cfg": new_cfg, "st": new_st},
    ).mappings().first()
    return dict(row) if row else None


def delete_source_row(conn: Connection, *, workspace_id: int, source_id: int) -> bool:
    r = conn.execute(
        text("DELETE FROM source WHERE id = :id AND workspace_id = :wid RETURNING id"),
        {"id": source_id, "wid": workspace_id},
    ).first()
    return r is not None


def list_destinations(conn: Connection, *, workspace_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        text(
            "SELECT id, workspace_id, name, connector_code, config_encrypted, status, created_by, "
            "created_at, updated_at, last_checked_at FROM destination WHERE workspace_id = :wid ORDER BY id"
        ),
        {"wid": workspace_id},
    ).mappings().all()
    return [dict(r) for r in rows]


def get_destination(conn: Connection, *, workspace_id: int, destination_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        text(
            "SELECT id, workspace_id, name, connector_code, config_encrypted, status, created_by, "
            "created_at, updated_at, last_checked_at FROM destination WHERE id = :id AND workspace_id = :wid"
        ),
        {"id": destination_id, "wid": workspace_id},
    ).mappings().first()
    return dict(row) if row else None


def create_destination_row(
    conn: Connection,
    *,
    workspace_id: int,
    name: str,
    connector_code: str,
    config: dict[str, Any],
    created_by: str | None,
) -> dict[str, Any]:
    row = conn.execute(
        text(
            "INSERT INTO destination (workspace_id, name, connector_code, config_encrypted, status, created_by, created_at, updated_at) "
            "VALUES (:wid, :name, :cc, :cfg, 'active', :cb, NOW(), NOW()) "
            "RETURNING id, workspace_id, name, connector_code, config_encrypted, status, created_by, "
            "created_at, updated_at, last_checked_at"
        ),
        {
            "wid": workspace_id,
            "name": name.strip(),
            "cc": connector_code.strip(),
            "cfg": _config_dump(config),
            "cb": created_by,
        },
    ).mappings().one()
    return dict(row)


def update_destination_row(
    conn: Connection,
    *,
    workspace_id: int,
    destination_id: int,
    name: str | None = None,
    connector_code: str | None = None,
    config: dict[str, Any] | None = None,
    status: str | None = None,
) -> dict[str, Any] | None:
    cur = get_destination(conn, workspace_id=workspace_id, destination_id=destination_id)
    if cur is None:
        return None
    new_name = name.strip() if name is not None else cur["name"]
    new_cc = connector_code.strip() if connector_code is not None else cur["connector_code"]
    new_cfg = _config_dump(config) if config is not None else cur["config_encrypted"]
    new_st = status.strip() if status is not None else cur["status"]
    row = conn.execute(
        text(
            "UPDATE destination SET name = :name, connector_code = :cc, config_encrypted = :cfg, status = :st, updated_at = NOW() "
            "WHERE id = :id AND workspace_id = :wid "
            "RETURNING id, workspace_id, name, connector_code, config_encrypted, status, created_by, "
            "created_at, updated_at, last_checked_at"
        ),
        {"id": destination_id, "wid": workspace_id, "name": new_name, "cc": new_cc, "cfg": new_cfg, "st": new_st},
    ).mappings().first()
    return dict(row) if row else None


def delete_destination_row(conn: Connection, *, workspace_id: int, destination_id: int) -> bool:
    r = conn.execute(
        text("DELETE FROM destination WHERE id = :id AND workspace_id = :wid RETURNING id"),
        {"id": destination_id, "wid": workspace_id},
    ).first()
    return r is not None


def _stream_rows_for_connection(conn: Connection, connection_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        text(
            "SELECT id, connection_id, stream_name, sync_mode, cursor_field, primary_key, is_enabled, "
            "cursor_value, mapping_profile_id FROM connection_stream WHERE connection_id = :cid ORDER BY stream_name"
        ),
        {"cid": connection_id},
    ).mappings().all()
    return [dict(r) for r in rows]


def list_connections(conn: Connection, *, workspace_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        text(
            "SELECT c.id, c.workspace_id, c.name, c.description, c.source_id, c.destination_id, c.status, "
            "c.schedule_cron, c.timezone, c.is_active, c.created_by, c.created_at, c.updated_at, "
            "(SELECT COUNT(*) FROM connection_stream cs WHERE cs.connection_id = c.id)::int AS stream_count "
            "FROM connection c WHERE c.workspace_id = :wid ORDER BY c.id"
        ),
        {"wid": workspace_id},
    ).mappings().all()
    return [dict(r) for r in rows]


def get_connection(conn: Connection, *, workspace_id: int, connection_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        text(
            "SELECT c.id, c.workspace_id, c.name, c.description, c.source_id, c.destination_id, c.status, "
            "c.schedule_cron, c.timezone, c.is_active, c.created_by, c.created_at, c.updated_at "
            "FROM connection c WHERE c.id = :id AND c.workspace_id = :wid"
        ),
        {"id": connection_id, "wid": workspace_id},
    ).mappings().first()
    if row is None:
        return None
    out = dict(row)
    out["streams"] = _stream_rows_for_connection(conn, connection_id)
    return out


def create_connection_row(
    conn: Connection,
    *,
    workspace_id: int,
    name: str,
    description: str | None,
    source_id: int,
    destination_id: int,
    schedule_cron: str | None,
    timezone: str,
    streams: list[dict[str, Any]],
    created_by: str | None,
) -> dict[str, Any]:
    src = get_source(conn, workspace_id=workspace_id, source_id=source_id)
    if src is None:
        raise EltRepoError("source not found")
    dst = get_destination(conn, workspace_id=workspace_id, destination_id=destination_id)
    if dst is None:
        raise EltRepoError("destination not found")

    crow = conn.execute(
        text(
            "INSERT INTO connection (workspace_id, name, description, source_id, destination_id, status, schedule_cron, timezone, is_active, created_by, created_at, updated_at) "
            "VALUES (:wid, :name, :descr, :sid, :did, 'active', :cron, :tz, true, :cb, NOW(), NOW()) "
            "RETURNING id, workspace_id, name, description, source_id, destination_id, status, schedule_cron, timezone, is_active, created_by, created_at, updated_at"
        ),
        {
            "wid": workspace_id,
            "name": name.strip(),
            "descr": description,
            "sid": source_id,
            "did": destination_id,
            "cron": schedule_cron,
            "tz": timezone.strip() or "UTC",
            "cb": created_by,
        },
    ).mappings().one()
    cid = int(crow["id"])
    ic = str(src["connector_code"])
    for s in streams:
        sn = str(s["stream_name"]).strip()
        sm = str(s.get("sync_mode") or "full_refresh").strip()
        cf = s.get("cursor_field")
        cf = str(cf).strip() if cf else None
        pk = s.get("primary_key")
        pk = str(pk) if pk is not None else None
        en = bool(s.get("is_enabled", True))
        mp = s.get("mapping_profile_id")
        mp_id = int(mp) if mp is not None else None
        csrow = conn.execute(
            text(
                "INSERT INTO connection_stream (connection_id, stream_name, sync_mode, cursor_field, primary_key, is_enabled, cursor_value, mapping_profile_id) "
                "VALUES (:cid, :sn, :sm, :cf, :pk, :en, NULL, :mp) "
                "RETURNING id"
            ),
            {"cid": cid, "sn": sn, "sm": sm, "cf": cf, "pk": pk, "en": en, "mp": mp_id},
        ).mappings().one()
        csid = int(csrow["id"])
        ensure_sync_state_for_stream(
            conn,
            integration_code=ic,
            stream_name=sn,
            sync_mode=sm,
            cursor_field=cf,
            connection_stream_id=csid,
        )
    return get_connection(conn, workspace_id=workspace_id, connection_id=cid) or dict(crow)


def update_connection_row(
    conn: Connection,
    *,
    workspace_id: int,
    connection_id: int,
    name: str | None = None,
    description: str | None = None,
    status: str | None = None,
    schedule_cron: str | None = None,
    timezone: str | None = None,
    is_active: bool | None = None,
) -> dict[str, Any] | None:
    exists = conn.execute(
        text("SELECT 1 FROM connection WHERE id = :id AND workspace_id = :wid"),
        {"id": connection_id, "wid": workspace_id},
    ).first()
    if exists is None:
        return None
    row = conn.execute(
        text(
            "UPDATE connection SET "
            "name = COALESCE(:name, name), "
            "description = COALESCE(:descr, description), "
            "status = COALESCE(:st, status), "
            "schedule_cron = COALESCE(:cron, schedule_cron), "
            "timezone = COALESCE(:tz, timezone), "
            "is_active = COALESCE(:ia, is_active), "
            "updated_at = NOW() "
            "WHERE id = :id AND workspace_id = :wid "
            "RETURNING id, workspace_id, name, description, source_id, destination_id, status, schedule_cron, timezone, is_active, created_by, created_at, updated_at"
        ),
        {
            "id": connection_id,
            "wid": workspace_id,
            "name": name.strip() if name is not None else None,
            "descr": description,
            "st": status.strip() if status is not None else None,
            "cron": schedule_cron,
            "tz": timezone.strip() if timezone is not None else None,
            "ia": is_active,
        },
    ).mappings().first()
    if row is None:
        return None
    out = dict(row)
    out["streams"] = _stream_rows_for_connection(conn, connection_id)
    return out


def delete_connection_row(conn: Connection, *, workspace_id: int, connection_id: int) -> bool:
    r = conn.execute(
        text("DELETE FROM connection WHERE id = :id AND workspace_id = :wid RETURNING id"),
        {"id": connection_id, "wid": workspace_id},
    ).first()
    return r is not None


def ensure_sync_state_for_stream(
    conn: Connection,
    *,
    integration_code: str,
    stream_name: str,
    sync_mode: str,
    cursor_field: str | None,
    connection_stream_id: int,
) -> None:
    cv = json.dumps({"cursor": None, "via": "elt_domain"}, ensure_ascii=False)
    ingest = json.dumps({"cursor": None, "rows_emitted": 0, "via": "elt_domain"}, ensure_ascii=False)
    conn.execute(
        text(
            "INSERT INTO sync_state (integration_code, stream_name, sync_mode, cursor_field, cursor_value, ingest_state, last_success_at, updated_at, connection_stream_id) "
            "VALUES (:ic, :sn, :sm, :cf, CAST(:cv AS text), CAST(:ingest AS jsonb), NULL, NOW(), :csid) "
            "ON CONFLICT (integration_code, stream_name) DO UPDATE SET "
            "sync_mode = EXCLUDED.sync_mode, cursor_field = EXCLUDED.cursor_field, "
            "connection_stream_id = EXCLUDED.connection_stream_id, updated_at = NOW()"
        ),
        {
            "ic": integration_code,
            "sn": stream_name,
            "sm": sync_mode,
            "cf": cursor_field,
            "cv": cv,
            "ingest": ingest,
            "csid": connection_stream_id,
        },
    )


def touch_source_checked(conn: Connection, *, workspace_id: int, source_id: int) -> None:
    conn.execute(
        text(
            "UPDATE source SET last_checked_at = NOW(), updated_at = NOW() WHERE id = :id AND workspace_id = :wid"
        ),
        {"id": source_id, "wid": workspace_id},
    )


def touch_destination_checked(conn: Connection, *, workspace_id: int, destination_id: int) -> None:
    conn.execute(
        text(
            "UPDATE destination SET last_checked_at = NOW(), updated_at = NOW() WHERE id = :id AND workspace_id = :wid"
        ),
        {"id": destination_id, "wid": workspace_id},
    )


def public_source_payload(row: dict[str, Any]) -> dict[str, Any]:
    d = dict(row)
    d["config"] = _config_load(str(d.get("config_encrypted") or ""))
    del d["config_encrypted"]
    return d


def public_destination_payload(row: dict[str, Any]) -> dict[str, Any]:
    d = dict(row)
    d["config"] = _config_load(str(d.get("config_encrypted") or ""))
    del d["config_encrypted"]
    return d
