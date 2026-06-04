"""CRUD и утилиты для доменных сущностей source / destination / connection (Фаза 4)."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from datanorma.elt.sync_mode_policy import (
    cursor_to_storage,
    destination_sync_mode_for_legacy,
    effective_source_sync_mode,
    primary_key_to_storage,
    validate_stream_sync_config,
)


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
    created_by_user_id: int | None = None,
) -> dict[str, Any]:
    row = conn.execute(
        text(
            "INSERT INTO source (workspace_id, name, connector_code, config_encrypted, status, created_by, created_by_user_id, created_at, updated_at) "
            "VALUES (:wid, :name, :cc, :cfg, 'active', :cb, :cbuid, NOW(), NOW()) "
            "RETURNING id, workspace_id, name, connector_code, config_encrypted, status, created_by, created_by_user_id, "
            "created_at, updated_at, last_checked_at"
        ),
        {
            "wid": workspace_id,
            "name": name.strip(),
            "cc": connector_code.strip(),
            "cfg": _config_dump(config),
            "cb": created_by,
            "cbuid": created_by_user_id,
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
    created_by_user_id: int | None = None,
) -> dict[str, Any]:
    row = conn.execute(
        text(
            "INSERT INTO destination (workspace_id, name, connector_code, config_encrypted, status, created_by, created_by_user_id, created_at, updated_at) "
            "VALUES (:wid, :name, :cc, :cfg, 'active', :cb, :cbuid, NOW(), NOW()) "
            "RETURNING id, workspace_id, name, connector_code, config_encrypted, status, created_by, created_by_user_id, "
            "created_at, updated_at, last_checked_at"
        ),
        {
            "wid": workspace_id,
            "name": name.strip(),
            "cc": connector_code.strip(),
            "cfg": _config_dump(config),
            "cb": created_by,
            "cbuid": created_by_user_id,
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
            "SELECT id, connection_id, stream_name, sync_mode, destination_sync_mode, cursor_field, primary_key, is_enabled, "
            "cursor_value, mapping_profile_id FROM connection_stream WHERE connection_id = :cid ORDER BY stream_name"
        ),
        {"cid": connection_id},
    ).mappings().all()
    return [dict(r) for r in rows]


def _connection_select_sql(with_streams_subcount: bool) -> str:
    cols = [
        "c.id",
        "c.workspace_id",
        "c.name",
        "c.description",
        "c.source_id",
        "c.destination_id",
        "c.status",
        "c.schedule_cron",
        "c.timezone",
        "c.is_active",
        "c.created_by",
        "c.created_at",
        "c.updated_at",
        "c.wizard_meta",
    ]
    if with_streams_subcount:
        cols.append("(SELECT COUNT(*) FROM connection_stream cs WHERE cs.connection_id = c.id)::int AS stream_count")
    cols.extend(
        [
            "s.name AS source_name",
            "s.connector_code AS source_connector_code",
            "d.name AS destination_name",
            "d.connector_code AS destination_connector_code",
        ]
    )
    return (
        "SELECT "
        + ", ".join(cols)
        + " FROM connection c "
        "LEFT JOIN source s ON s.id = c.source_id AND s.workspace_id = c.workspace_id "
        "LEFT JOIN destination d ON d.id = c.destination_id AND d.workspace_id = c.workspace_id "
    )


def list_connections(conn: Connection, *, workspace_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        text(_connection_select_sql(with_streams_subcount=True) + "WHERE c.workspace_id = :wid ORDER BY c.id"),
        {"wid": workspace_id},
    ).mappings().all()
    return [dict(r) for r in rows]


def list_connection_schedules(conn: Connection, *, workspace_id: int) -> list[dict[str, Any]]:
    """Подключения workspace с непустым schedule_cron (для /api/v1/schedules)."""
    out: list[dict[str, Any]] = []
    for row in list_connections(conn, workspace_id=workspace_id):
        cron = str(row.get("schedule_cron") or "").strip()
        if not cron:
            continue
        item = dict(row)
        item["connection_name"] = row.get("name")
        item["last_run_at"] = _last_sync_run_at_for_connection(conn, connection_id=int(row["id"]))
        out.append(item)
    return out


def _last_sync_run_at_for_connection(conn: Connection, *, connection_id: int) -> Any:
    try:
        return conn.execute(
            text(
                "SELECT MAX(COALESCE(finished_at, started_at, created_at)) "
                "FROM sync_run WHERE domain_connection_id = :cid"
            ),
            {"cid": connection_id},
        ).scalar()
    except Exception:
        return None


def get_connection(conn: Connection, *, workspace_id: int, connection_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        text(
            _connection_select_sql(with_streams_subcount=False)
            + "WHERE c.id = :id AND c.workspace_id = :wid"
        ),
        {"id": connection_id, "wid": workspace_id},
    ).mappings().first()
    if row is None:
        return None
    out = dict(row)
    cs_rows = _stream_rows_for_connection(conn, connection_id)
    out["streams"] = cs_rows
    out["stream_count"] = len(cs_rows)
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
    column_rules: list[dict[str, Any]] | None = None,
    wizard_meta: dict[str, Any] | None = None,
    created_by: str | None,
    created_by_user_id: int | None = None,
) -> dict[str, Any]:
    src = get_source(conn, workspace_id=workspace_id, source_id=source_id)
    if src is None:
        raise EltRepoError("source not found")
    dst = get_destination(conn, workspace_id=workspace_id, destination_id=destination_id)
    if dst is None:
        raise EltRepoError("destination not found")

    wm_json = json.dumps(wizard_meta, ensure_ascii=False) if wizard_meta else None
    crow = conn.execute(
        text(
            "INSERT INTO connection (workspace_id, name, description, source_id, destination_id, status, schedule_cron, timezone, is_active, created_by, created_by_user_id, wizard_meta, created_at, updated_at) "
            "VALUES (:wid, :name, :descr, :sid, :did, 'active', :cron, :tz, true, :cb, :cbuid, CAST(:wm AS jsonb), NOW(), NOW()) "
            "RETURNING id"
        ),
        {
            "wid": workspace_id,
            "name": name.strip(),
            "descr": description,
            "sid": source_id,
            "did": destination_id,
            "cron": schedule_cron,
            "tz": timezone.strip() or "UTC",
            "cbuid": created_by_user_id,
            "cb": created_by,
            "wm": wm_json,
        },
    ).mappings().one()
    cid = int(crow["id"])
    ic = str(src["connector_code"])
    stream_sync_defaults: dict[str, dict[str, Any]] = {}
    for s in streams:
        sn = str(s["stream_name"]).strip()
        sm = str(s.get("sync_mode") or "full_refresh").strip()
        dsm = s.get("destination_sync_mode")
        dsm = str(dsm).strip() if dsm else destination_sync_mode_for_legacy(sm)
        cf_raw = s.get("cursor_field")
        cf = cursor_to_storage(cf_raw)
        pk_raw = s.get("primary_key")
        pk = primary_key_to_storage(pk_raw)
        errs = validate_stream_sync_config(
            sync_mode=sm,
            destination_sync_mode=dsm,
            cursor_field=cf_raw,
            primary_key=pk_raw,
        )
        if errs:
            raise EltRepoError("; ".join(errs))
        sm = effective_source_sync_mode(sync_mode=sm, destination_sync_mode=dsm)
        en = bool(s.get("is_enabled", True))
        mp = s.get("mapping_profile_id")
        mp_id = int(mp) if mp is not None else None
        stream_sync_defaults[sn] = {"sync_mode": sm, "cursor_field": cf, "destination_sync_mode": dsm}
        csrow = conn.execute(
            text(
                "INSERT INTO connection_stream (connection_id, stream_name, sync_mode, destination_sync_mode, cursor_field, primary_key, is_enabled, cursor_value, mapping_profile_id) "
                "VALUES (:cid, :sn, :sm, :dsm, :cf, :pk, :en, NULL, :mp) "
                "RETURNING id"
            ),
            {"cid": cid, "sn": sn, "sm": sm, "dsm": dsm, "cf": cf, "pk": pk, "en": en, "mp": mp_id},
        ).mappings().one()
        csid = int(csrow["id"])
        ensure_sync_state_for_stream(
            conn,
            integration_code=ic,
            stream_name=sn,
            sync_mode=sm,
            cursor_field=cf,
            connection_stream_id=csid,
            workspace_id=workspace_id,
        )

    if column_rules:
        from datanorma.web.connector_schema_meta import stream_default_for

        by_entity: dict[str, list[dict[str, Any]]] = {}
        for rule in column_rules:
            entity = rule.get("entity")
            sn = str(entity).strip() if entity else None
            if not sn and len(streams) == 1:
                sn = str(streams[0]["stream_name"]).strip()
            if not sn:
                continue
            by_entity.setdefault(sn, []).append(rule)

        for sn, cols in by_entity.items():
            defaults = stream_sync_defaults.get(sn) or stream_default_for(ic, sn)
            save_connection_stream_rules(
                conn,
                connection_id=cid,
                stream_name=sn,
                sync_mode=str(defaults.get("sync_mode") or "full_refresh"),
                cursor_field=defaults.get("cursor_field"),
                columns=cols,
            )

    return get_connection(conn, workspace_id=workspace_id, connection_id=cid) or {"id": cid}


def _primary_key_list_from_storage(pk_raw: Any) -> list[str]:
    if pk_raw is None:
        return []
    if isinstance(pk_raw, list):
        return [str(x).strip() for x in pk_raw if str(x).strip()]
    if isinstance(pk_raw, str):
        text = pk_raw.strip()
        if not text:
            return []
        if text.startswith("["):
            try:
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    return [str(x).strip() for x in parsed if str(x).strip()]
            except json.JSONDecodeError:
                pass
        if "," in text:
            return [p.strip() for p in text.split(",") if p.strip()]
        return [text]
    return []


def update_connection_streams_config(
    conn: Connection,
    *,
    workspace_id: int,
    connection_id: int,
    streams: list[dict[str, Any]] | None = None,
    column_rules: list[dict[str, Any]] | None = None,
    wizard_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Обновить режимы потоков и правила колонок существующего подключения."""
    row = get_connection(conn, workspace_id=workspace_id, connection_id=connection_id)
    if row is None:
        raise EltRepoError("connection not found")
    src = get_source(conn, workspace_id=workspace_id, source_id=int(row["source_id"]))
    if src is None:
        raise EltRepoError("source not found")
    ic = str(src["connector_code"])
    existing_by_name = {str(s["stream_name"]): s for s in row.get("streams") or []}
    stream_sync_defaults: dict[str, dict[str, Any]] = {}

    if streams:
        for s in streams:
            sn = str(s.get("stream_name") or "").strip()
            if not sn:
                raise EltRepoError("stream_name is required")
            if sn not in existing_by_name:
                raise EltRepoError(f"stream not found: {sn}")
            sm = str(s.get("sync_mode") or "full_refresh").strip()
            dsm = s.get("destination_sync_mode")
            dsm = str(dsm).strip() if dsm else destination_sync_mode_for_legacy(sm)
            cf_raw = s.get("cursor_field")
            cf = cursor_to_storage(cf_raw)
            pk_raw = s.get("primary_key")
            pk = primary_key_to_storage(pk_raw)
            errs = validate_stream_sync_config(
                sync_mode=sm,
                destination_sync_mode=dsm,
                cursor_field=cf_raw,
                primary_key=pk_raw,
            )
            if errs:
                raise EltRepoError("; ".join(errs))
            sm_eff = effective_source_sync_mode(sync_mode=sm, destination_sync_mode=dsm)
            en = bool(s.get("is_enabled", existing_by_name[sn].get("is_enabled", True)))
            mp = s.get("mapping_profile_id")
            mp_id = int(mp) if mp is not None else existing_by_name[sn].get("mapping_profile_id")
            updated = conn.execute(
                text(
                    "UPDATE connection_stream SET sync_mode = :sm, destination_sync_mode = :dsm, "
                    "cursor_field = :cf, primary_key = :pk, is_enabled = :en, mapping_profile_id = :mp, updated_at = NOW() "
                    "WHERE connection_id = :cid AND stream_name = :sn RETURNING id"
                ),
                {
                    "sm": sm_eff,
                    "dsm": dsm,
                    "cf": cf,
                    "pk": pk,
                    "en": en,
                    "mp": mp_id,
                    "cid": connection_id,
                    "sn": sn,
                },
            ).first()
            if updated is None:
                raise EltRepoError(f"stream update failed: {sn}")
            csid = int(updated[0])
            ensure_sync_state_for_stream(
                conn,
                integration_code=ic,
                stream_name=sn,
                sync_mode=sm_eff,
                cursor_field=cf,
                connection_stream_id=csid,
                workspace_id=workspace_id,
            )
            stream_sync_defaults[sn] = {
                "sync_mode": sm_eff,
                "cursor_field": cf,
                "destination_sync_mode": dsm,
                "primary_key": _primary_key_list_from_storage(pk_raw),
            }

    if column_rules:
        from datanorma.web.connector_schema_meta import stream_default_for

        by_entity: dict[str, list[dict[str, Any]]] = {}
        for rule in column_rules:
            entity = rule.get("entity")
            sn = str(entity).strip() if entity else None
            if not sn and len(existing_by_name) == 1:
                sn = next(iter(existing_by_name.keys()))
            if not sn:
                continue
            by_entity.setdefault(sn, []).append(rule)

        for sn, cols in by_entity.items():
            if sn not in existing_by_name:
                raise EltRepoError(f"stream not found for column rules: {sn}")
            defaults = stream_sync_defaults.get(sn)
            if defaults is None:
                ex = existing_by_name[sn]
                defaults = {
                    "sync_mode": str(ex.get("sync_mode") or "full_refresh"),
                    "cursor_field": ex.get("cursor_field"),
                    "primary_key": _primary_key_list_from_storage(ex.get("primary_key")),
                }
                if defaults.get("sync_mode") is None:
                    defaults = stream_default_for(ic, sn)
            save_connection_stream_rules(
                conn,
                connection_id=connection_id,
                stream_name=sn,
                sync_mode=str(defaults.get("sync_mode") or "full_refresh"),
                cursor_field=defaults.get("cursor_field"),
                primary_key=defaults.get("primary_key") or [],
                columns=cols,
            )

    if wizard_meta is not None:
        wm_existing = row.get("wizard_meta")
        if wm_existing is not None and not isinstance(wm_existing, dict):
            try:
                wm_existing = json.loads(wm_existing) if isinstance(wm_existing, str) else None
            except json.JSONDecodeError:
                wm_existing = None
        merged: dict[str, Any] = dict(wm_existing) if isinstance(wm_existing, dict) else {}
        merged.update(wizard_meta)
        conn.execute(
            text(
                "UPDATE connection SET wizard_meta = CAST(:wm AS jsonb), updated_at = NOW() "
                "WHERE id = :id AND workspace_id = :wid"
            ),
            {
                "wm": json.dumps(merged, ensure_ascii=False),
                "id": connection_id,
                "wid": workspace_id,
            },
        )

    out = get_connection(conn, workspace_id=workspace_id, connection_id=connection_id)
    if out is None:
        raise EltRepoError("connection not found")
    return out


def patch_connection_row(
    conn: Connection,
    *,
    workspace_id: int,
    connection_id: int,
    fields: dict[str, Any],
) -> dict[str, Any] | None:
    """Применить частичное обновление connection (в т.ч. schedule_cron=NULL)."""
    streams = fields.pop("streams", None)
    column_rules = fields.pop("column_rules", None)
    wizard_meta = fields.pop("wizard_meta", None)
    if streams is not None or column_rules is not None or wizard_meta is not None:
        try:
            update_connection_streams_config(
                conn,
                workspace_id=workspace_id,
                connection_id=connection_id,
                streams=streams,
                column_rules=column_rules,
                wizard_meta=wizard_meta,
            )
        except EltRepoError:
            raise
    allowed = {"name", "description", "status", "schedule_cron", "timezone", "is_active"}
    patch = {k: v for k, v in fields.items() if k in allowed}
    if not patch:
        return get_connection(conn, workspace_id=workspace_id, connection_id=connection_id)
    exists = conn.execute(
        text("SELECT 1 FROM connection WHERE id = :id AND workspace_id = :wid"),
        {"id": connection_id, "wid": workspace_id},
    ).first()
    if exists is None:
        return None
    sets: list[str] = []
    params: dict[str, Any] = {"id": connection_id, "wid": workspace_id}
    for k, v in patch.items():
        if k == "name" and v is not None:
            v = str(v).strip()
        elif k == "status" and v is not None:
            v = str(v).strip()
        elif k == "timezone" and v is not None:
            v = str(v).strip()
        sets.append(f"{k} = :{k}")
        params[k] = v
    conn.execute(
        text("UPDATE connection SET " + ", ".join(sets) + ", updated_at = NOW() WHERE id = :id AND workspace_id = :wid"),
        params,
    )
    return get_connection(conn, workspace_id=workspace_id, connection_id=connection_id)


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
    """Обновить только переданные не-None поля (schedule_cron=None здесь не передаётся — значит не менять)."""
    fields: dict[str, Any] = {}
    if name is not None:
        fields["name"] = name.strip()
    if description is not None:
        fields["description"] = description
    if status is not None:
        fields["status"] = status.strip()
    if schedule_cron is not None:
        fields["schedule_cron"] = schedule_cron
    if timezone is not None:
        fields["timezone"] = timezone.strip()
    if is_active is not None:
        fields["is_active"] = is_active
    if not fields:
        return get_connection(conn, workspace_id=workspace_id, connection_id=connection_id)
    return patch_connection_row(conn, workspace_id=workspace_id, connection_id=connection_id, fields=fields)


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
    workspace_id: int | None = None,
) -> None:
    """Создаёт или обновляет sync_state для одного connection_stream (не переиспользует чужие строки)."""
    cv = json.dumps({"cursor": None, "via": "elt_domain"}, ensure_ascii=False)
    ingest = json.dumps({"cursor": None, "rows_emitted": 0, "via": "elt_domain"}, ensure_ascii=False)
    existing = conn.execute(
        text("SELECT id FROM sync_state WHERE connection_stream_id = :csid"),
        {"csid": connection_stream_id},
    ).first()
    if existing is not None:
        conn.execute(
            text(
                "UPDATE sync_state SET sync_mode = :sm, cursor_field = :cf, updated_at = NOW() "
                "WHERE connection_stream_id = :csid"
            ),
            {"sm": sync_mode, "cf": cursor_field, "csid": connection_stream_id},
        )
        return

    cols = (
        "integration_code, stream_name, sync_mode, cursor_field, cursor_value, ingest_state, "
        "last_success_at, updated_at, connection_stream_id"
    )
    vals = (
        ":ic, :sn, :sm, :cf, CAST(:cv AS text), CAST(:ingest AS jsonb), NULL, NOW(), :csid"
    )
    params: dict[str, Any] = {
        "ic": integration_code,
        "sn": stream_name,
        "sm": sync_mode,
        "cf": cursor_field,
        "cv": cv,
        "ingest": ingest,
        "csid": connection_stream_id,
    }
    if workspace_id is not None:
        cols += ", workspace_id"
        vals += ", :wid"
        params["wid"] = workspace_id
    conn.execute(
        text(f"INSERT INTO sync_state ({cols}) VALUES ({vals})"),
        params,
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


def save_connection_stream_rules(
    conn: Connection,
    *,
    connection_id: int,
    stream_name: str,
    sync_mode: str,
    cursor_field: str | None,
    columns: list[dict[str, Any]],
    primary_key: list[str] | None = None,
) -> None:
    """Upsert stream-level rules and column rules for a connection."""
    try:
        stream_rules_id = conn.execute(
            text(
                """
                INSERT INTO connection_stream_rules (connection_id, stream_name, sync_mode, cursor_field, primary_key, drop_unknown_columns, deduplicate, enabled)
                VALUES (:cid, :sn, COALESCE(:sm, 'full_refresh'), :cf, COALESCE(CAST(:pk AS jsonb), '[]'::jsonb), FALSE, TRUE, TRUE)
                ON CONFLICT (connection_id, stream_name) DO UPDATE SET
                  sync_mode = EXCLUDED.sync_mode,
                  cursor_field = EXCLUDED.cursor_field,
                  primary_key = EXCLUDED.primary_key,
                  enabled = TRUE,
                  updated_at = NOW()
                RETURNING id
                """
            ),
            {
                "cid": connection_id,
                "sn": stream_name,
                "sm": sync_mode,
                "cf": cursor_field,
                "pk": primary_key or [],
            },
        ).scalar()

        if stream_rules_id is None:
            return
        conn.execute(text("DELETE FROM connection_column_rule WHERE stream_rules_id = :rid"), {"rid": stream_rules_id})
        for idx, c in enumerate(columns):
            if not isinstance(c, dict):
                continue
            conn.execute(
                text(
                    """
                    INSERT INTO connection_column_rule
                      (stream_rules_id, source_field, target_field, type, nullable, required, params, on_error, sort_order, description)
                    VALUES
                      (:rid, :sf, :tf, :tp, TRUE, COALESCE(:req, FALSE), '{}'::jsonb, 'null', :so, NULL)
                    """
                ),
                {
                    "rid": stream_rules_id,
                    "sf": str(c.get("source_field") or ""),
                    "tf": str(c.get("target_field") or c.get("source_field") or ""),
                    "tp": str(c.get("type") or "string"),
                    "req": bool(c.get("required", False)),
                    "so": idx,
                },
            )
    except Exception:
        return


def load_connection_column_rules(conn: Connection, *, connection_id: int) -> list[dict[str, Any]]:
    """All column rules for a connection (flat list with entity = stream_name)."""
    try:
        rows = conn.execute(
            text(
                """
                SELECT csr.stream_name, ccr.source_field, ccr.target_field, ccr.type, ccr.required
                FROM connection_column_rule ccr
                JOIN connection_stream_rules csr ON csr.id = ccr.stream_rules_id
                WHERE csr.connection_id = :cid AND csr.enabled IS TRUE
                ORDER BY csr.stream_name, ccr.sort_order, ccr.id
                """
            ),
            {"cid": connection_id},
        ).mappings().all()
        return [
            {
                "entity": r["stream_name"],
                "source_field": r["source_field"],
                "target_field": r["target_field"],
                "type": r["type"],
                "required": bool(r["required"]),
            }
            for r in rows
        ]
    except Exception:
        return []


def load_stream_rules_for_sync(
    conn: Connection,
    *,
    connection_id: int,
    stream_name: str,
) -> "StreamRules | None":
    from datanorma.normalization.rules import ColumnRule, StreamRules

    try:
        sr = conn.execute(
            text(
                """
                SELECT id, stream_name, sync_mode, cursor_field, primary_key, drop_unknown_columns, deduplicate
                FROM connection_stream_rules
                WHERE connection_id = :cid AND stream_name = :sn AND enabled IS TRUE
                """
            ),
            {"cid": connection_id, "sn": stream_name},
        ).mappings().first()
        if sr is None:
            return None
        cols_rows = conn.execute(
            text(
                """
                SELECT source_field, target_field, type, nullable, required, params, on_error
                FROM connection_column_rule
                WHERE stream_rules_id = :rid
                ORDER BY sort_order, id
                """
            ),
            {"rid": int(sr["id"])},
        ).mappings().all()
        columns: list[ColumnRule] = []
        for c in cols_rows:
            columns.append(
                ColumnRule(
                    source_field=str(c["source_field"]),
                    target_field=str(c["target_field"]),
                    type=str(c["type"]),  # type: ignore[arg-type]
                    nullable=bool(c.get("nullable", True)),
                    required=bool(c.get("required", False)),
                    on_error=str(c.get("on_error") or "null"),  # type: ignore[arg-type]
                )
            )
        pk = sr.get("primary_key") or []
        if isinstance(pk, str):
            try:
                pk = json.loads(pk)
            except json.JSONDecodeError:
                pk = []
        return StreamRules(
            stream_name=str(sr["stream_name"]),
            primary_key=list(pk) if isinstance(pk, list) else [],
            cursor_field=sr.get("cursor_field"),
            sync_mode=str(sr.get("sync_mode") or "full_refresh"),  # type: ignore[arg-type]
            columns=columns,
            drop_unknown_columns=bool(sr.get("drop_unknown_columns")),
            deduplicate=bool(sr.get("deduplicate", True)),
        )
    except Exception:
        return None


def _parse_legacy_wizard_meta(description: str | None) -> dict[str, Any] | None:
    if not description:
        return None
    marker = "__DATANORMA_WIZARD__:"
    idx = description.rfind(marker)
    if idx < 0:
        return None
    try:
        raw = description[idx + len(marker) :].strip()
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def public_connection_payload(conn: Connection, row: dict[str, Any]) -> dict[str, Any]:
    """Public API shape for connection with column_rules and wizard_meta."""
    out = dict(row)
    wm = out.get("wizard_meta")
    if wm is not None and not isinstance(wm, dict):
        try:
            wm = json.loads(wm) if isinstance(wm, str) else None
        except json.JSONDecodeError:
            wm = None
    if wm is None:
        wm = _parse_legacy_wizard_meta(out.get("description"))
    out["wizard_meta"] = wm
    cid = int(out["id"])
    rules = load_connection_column_rules(conn, connection_id=cid)
    if not rules and wm and isinstance(wm.get("column_rules"), list):
        rules = []
        for r in wm["column_rules"]:
            if not isinstance(r, dict):
                continue
            rules.append(
                {
                    "entity": r.get("entity") or r.get("stream"),
                    "source_field": r.get("source_field"),
                    "target_field": r.get("target_field"),
                    "type": r.get("type"),
                    "required": bool(r.get("required", False)),
                }
            )
    out["column_rules"] = rules
    return out
