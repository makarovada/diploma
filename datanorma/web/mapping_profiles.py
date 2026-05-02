"""Сервис управления профилями маппинга и версиями."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine


class MappingProfileError(RuntimeError):
    """Ошибки бизнес-операций над mapping profiles."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def resolve_workspace_id(conn: Connection, workspace_code: str = "main") -> int:
    row = conn.execute(
        text("SELECT id FROM workspace WHERE code = :c ORDER BY id LIMIT 1"),
        {"c": workspace_code},
    ).mappings().first()
    if row is None:
        raise MappingProfileError(f"Workspace not found: {workspace_code}")
    return int(row["id"])


def _ensure_profile(
    conn: Connection,
    *,
    workspace_id: int,
    source_type: str,
    stream_name: str,
    profile_name: str,
    updated_by: str,
) -> int:
    row = conn.execute(
        text(
            "INSERT INTO mapping_profile (workspace_id, source_type, stream_name, profile_name, is_active, updated_at, updated_by) "
            "VALUES (:wid, :st, :sn, :pn, false, NOW(), :ub) "
            "ON CONFLICT ON CONSTRAINT uq_mapping_profile_scope_name DO UPDATE SET updated_at = NOW(), updated_by = :ub "
            "RETURNING id"
        ),
        {
            "wid": workspace_id,
            "st": source_type.strip(),
            "sn": stream_name.strip(),
            "pn": profile_name.strip(),
            "ub": updated_by,
        },
    ).mappings().one()
    return int(row["id"])


def _next_version(conn: Connection, profile_id: int) -> int:
    n = conn.execute(
        text("SELECT COALESCE(MAX(version), 0) FROM mapping_profile_version WHERE profile_id = :pid"),
        {"pid": profile_id},
    ).scalar_one()
    return int(n) + 1


def create_draft_version(
    conn: Connection,
    *,
    workspace_id: int,
    source_type: str,
    stream_name: str,
    profile_name: str,
    rules_json: dict[str, Any],
    created_by: str,
    change_note: str | None = None,
) -> dict[str, Any]:
    profile_id = _ensure_profile(
        conn,
        workspace_id=workspace_id,
        source_type=source_type,
        stream_name=stream_name,
        profile_name=profile_name,
        updated_by=created_by,
    )
    version = _next_version(conn, profile_id)
    row = conn.execute(
        text(
            "INSERT INTO mapping_profile_version (profile_id, version, status, rules_json, change_note, created_at, created_by) "
            "VALUES (:pid, :v, 'draft', CAST(:rj AS jsonb), :cn, NOW(), :cb) "
            "RETURNING id, profile_id, version, status, rules_json, change_note, created_at, created_by"
        ),
        {
            "pid": profile_id,
            "v": version,
            "rj": json.dumps(rules_json, ensure_ascii=False),
            "cn": change_note,
            "cb": created_by,
        },
    ).mappings().one()
    return dict(row)


def publish_version(conn: Connection, *, profile_id: int, version_id: int) -> dict[str, Any]:
    row = conn.execute(
        text(
            "UPDATE mapping_profile_version SET status = 'published' "
            "WHERE id = :id AND profile_id = :pid "
            "RETURNING id, profile_id, version, status, rules_json, change_note, created_at, created_by"
        ),
        {"id": version_id, "pid": profile_id},
    ).mappings().first()
    if row is None:
        raise MappingProfileError("Version not found for publish")
    return dict(row)


def activate_profile_version(
    conn: Connection,
    *,
    profile_id: int,
    version_id: int,
    updated_by: str,
) -> dict[str, Any]:
    p = conn.execute(
        text("SELECT id, workspace_id, source_type, stream_name FROM mapping_profile WHERE id = :id"),
        {"id": profile_id},
    ).mappings().first()
    if p is None:
        raise MappingProfileError("Profile not found")

    v = conn.execute(
        text("SELECT id, status FROM mapping_profile_version WHERE id = :id AND profile_id = :pid"),
        {"id": version_id, "pid": profile_id},
    ).mappings().first()
    if v is None:
        raise MappingProfileError("Version not found")
    if v["status"] != "published":
        raise MappingProfileError("Only published version can be activated")

    conn.execute(
        text(
            "UPDATE mapping_profile SET is_active = false, active_version_id = NULL, updated_at = NOW(), updated_by = :ub "
            "WHERE workspace_id = :wid AND source_type = :st AND stream_name = :sn"
        ),
        {"wid": p["workspace_id"], "st": p["source_type"], "sn": p["stream_name"], "ub": updated_by},
    )
    row = conn.execute(
        text(
            "UPDATE mapping_profile SET is_active = true, active_version_id = :vid, updated_at = NOW(), updated_by = :ub "
            "WHERE id = :pid "
            "RETURNING id, workspace_id, source_type, stream_name, profile_name, active_version_id, is_active, updated_at, updated_by"
        ),
        {"pid": profile_id, "vid": version_id, "ub": updated_by},
    ).mappings().one()
    return dict(row)


def rollback_to_version(
    conn: Connection,
    *,
    profile_id: int,
    version_id: int,
    updated_by: str,
    note: str | None = None,
) -> dict[str, Any]:
    src = conn.execute(
        text(
            "SELECT p.workspace_id, p.source_type, p.stream_name, p.profile_name, "
            "v.rules_json, v.version FROM mapping_profile p "
            "JOIN mapping_profile_version v ON v.profile_id = p.id "
            "WHERE p.id = :pid AND v.id = :vid"
        ),
        {"pid": profile_id, "vid": version_id},
    ).mappings().first()
    if src is None:
        raise MappingProfileError("Rollback source version not found")
    draft = create_draft_version(
        conn,
        workspace_id=int(src["workspace_id"]),
        source_type=str(src["source_type"]),
        stream_name=str(src["stream_name"]),
        profile_name=str(src["profile_name"]),
        rules_json=dict(src["rules_json"]),
        created_by=updated_by,
        change_note=note or f"Rollback from v{src['version']}",
    )
    pub = publish_version(conn, profile_id=profile_id, version_id=int(draft["id"]))
    activate_profile_version(conn, profile_id=profile_id, version_id=int(pub["id"]), updated_by=updated_by)
    return pub


def list_profiles(conn: Connection, workspace_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        text(
            "SELECT p.id, p.workspace_id, p.source_type, p.stream_name, p.profile_name, p.active_version_id, "
            "p.is_active, p.updated_at, p.updated_by, v.version AS active_version, v.status AS active_status "
            "FROM mapping_profile p "
            "LEFT JOIN mapping_profile_version v ON v.id = p.active_version_id "
            "WHERE p.workspace_id = :wid "
            "ORDER BY p.source_type, p.stream_name, p.profile_name, p.id"
        ),
        {"wid": workspace_id},
    ).mappings().all()
    return [dict(r) for r in rows]


def list_versions(conn: Connection, profile_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        text(
            "SELECT id, profile_id, version, status, rules_json, change_note, created_at, created_by "
            "FROM mapping_profile_version WHERE profile_id = :pid "
            "ORDER BY version DESC, id DESC"
        ),
        {"pid": profile_id},
    ).mappings().all()
    return [dict(r) for r in rows]


def get_active_source_rules(
    conn: Connection,
    *,
    workspace_id: int,
    source_type: str,
    stream_name: str,
) -> dict[str, Any] | None:
    row = conn.execute(
        text(
            "SELECT v.rules_json "
            "FROM mapping_profile p "
            "JOIN mapping_profile_version v ON v.id = p.active_version_id "
            "WHERE p.workspace_id = :wid AND p.source_type = :st AND p.stream_name = :sn AND p.is_active = true "
            "LIMIT 1"
        ),
        {"wid": workspace_id, "st": source_type, "sn": stream_name},
    ).mappings().first()
    if row is None:
        return None
    return dict(row["rules_json"])


def get_all_active_source_rules(conn: Connection, *, workspace_id: int) -> dict[tuple[str, str], dict[str, Any]]:
    rows = conn.execute(
        text(
            "SELECT p.source_type, p.stream_name, v.rules_json "
            "FROM mapping_profile p "
            "JOIN mapping_profile_version v ON v.id = p.active_version_id "
            "WHERE p.workspace_id = :wid AND p.is_active = true"
        ),
        {"wid": workspace_id},
    ).mappings().all()
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for r in rows:
        out[(str(r["source_type"]), str(r["stream_name"]))] = dict(r["rules_json"])
    return out


def load_mappings_with_db_override(
    *,
    base_mappings: dict[str, Any],
    engine: Engine,
    workspace_code: str = "main",
) -> dict[str, Any]:
    with engine.begin() as conn:
        workspace_id = resolve_workspace_id(conn, workspace_code=workspace_code)
        overrides = get_all_active_source_rules(conn, workspace_id=workspace_id)
    if not overrides:
        return base_mappings
    merged = dict(base_mappings)
    merged_sources = dict(merged.get("sources") or {})
    for (source_type, _stream_name), rules in overrides.items():
        merged_sources[source_type] = rules
    merged["sources"] = merged_sources
    merged["storage"] = "db_active_profile"
    merged["loaded_at"] = _utc_now().isoformat()
    return merged
