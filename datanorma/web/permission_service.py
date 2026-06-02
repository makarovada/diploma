"""Проверка и управление правами workspace и object-level grants."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from datanorma.web.permission_catalog import (
    GRANT_LEVEL_TO_WORKSPACE_PERM,
    PERMISSION_TO_GRANT_LEVEL,
    grant_level_covers,
)


class PermissionDenied(Exception):
    pass


@dataclass
class ResourceRef:
    resource_type: str
    resource_id: int


@dataclass
class WorkspaceAuthContext:
    user_id: int
    workspace_id: int
    is_admin: bool = False
    permissions: frozenset[str] = field(default_factory=frozenset)


def _grant_level_for_permission(permission: str) -> str | None:
    return PERMISSION_TO_GRANT_LEVEL.get(permission)


def is_workspace_member(conn: Connection, *, user_id: int, workspace_id: int) -> bool:
    row = conn.execute(
        text("SELECT 1 FROM user_workspace WHERE user_id = :uid AND workspace_id = :wid"),
        {"uid": user_id, "wid": workspace_id},
    ).first()
    return row is not None


def is_workspace_admin(conn: Connection, *, user_id: int, workspace_id: int) -> bool:
    row = conn.execute(
        text(
            "SELECT is_admin FROM user_workspace WHERE user_id = :uid AND workspace_id = :wid"
        ),
        {"uid": user_id, "wid": workspace_id},
    ).mappings().first()
    return bool(row and row["is_admin"])


def load_workspace_auth_context(
    conn: Connection, *, user_id: int, workspace_id: int
) -> WorkspaceAuthContext | None:
    if not is_workspace_member(conn, user_id=user_id, workspace_id=workspace_id):
        return None
    admin = is_workspace_admin(conn, user_id=user_id, workspace_id=workspace_id)
    if admin:
        return WorkspaceAuthContext(user_id=user_id, workspace_id=workspace_id, is_admin=True, permissions=frozenset())
    rows = conn.execute(
        text(
            "SELECT permission_code FROM workspace_member_permission "
            "WHERE workspace_id = :wid AND user_id = :uid"
        ),
        {"wid": workspace_id, "uid": user_id},
    ).fetchall()
    perms = frozenset(str(r[0]) for r in rows)
    return WorkspaceAuthContext(
        user_id=user_id, workspace_id=workspace_id, is_admin=False, permissions=perms
    )


def list_member_permissions(conn: Connection, *, workspace_id: int, user_id: int) -> list[str]:
    rows = conn.execute(
        text(
            "SELECT permission_code FROM workspace_member_permission "
            "WHERE workspace_id = :wid AND user_id = :uid ORDER BY permission_code"
        ),
        {"wid": workspace_id, "uid": user_id},
    ).fetchall()
    return [str(r[0]) for r in rows]


def set_member_permissions(
    conn: Connection,
    *,
    workspace_id: int,
    user_id: int,
    permission_codes: list[str],
) -> None:
    conn.execute(
        text("DELETE FROM workspace_member_permission WHERE workspace_id = :wid AND user_id = :uid"),
        {"wid": workspace_id, "uid": user_id},
    )
    for code in permission_codes:
        conn.execute(
            text(
                "INSERT INTO workspace_member_permission (workspace_id, user_id, permission_code) "
                "VALUES (:wid, :uid, :code) ON CONFLICT DO NOTHING"
            ),
            {"wid": workspace_id, "uid": user_id, "code": code},
        )


def _resource_owner_user_id(
    conn: Connection, *, workspace_id: int, resource: ResourceRef
) -> int | None:
    table = resource.resource_type
    if table not in ("source", "destination", "connection"):
        return None
    row = conn.execute(
        text(
            f"SELECT created_by_user_id FROM {table} "
            "WHERE id = :rid AND workspace_id = :wid"
        ),
        {"rid": resource.resource_id, "wid": workspace_id},
    ).mappings().first()
    if row is None:
        return None
    uid = row.get("created_by_user_id")
    return int(uid) if uid is not None else None


def _resource_grant_level(
    conn: Connection,
    *,
    workspace_id: int,
    resource: ResourceRef,
    grantee_user_id: int,
) -> str | None:
    row = conn.execute(
        text(
            "SELECT level FROM resource_grant "
            "WHERE workspace_id = :wid AND resource_type = :rt AND resource_id = :rid "
            "AND grantee_user_id = :uid"
        ),
        {
            "wid": workspace_id,
            "rt": resource.resource_type,
            "rid": resource.resource_id,
            "uid": grantee_user_id,
        },
    ).mappings().first()
    return str(row["level"]) if row else None


def authorize(
    ctx: WorkspaceAuthContext,
    conn: Connection,
    *,
    permission: str,
    resource: ResourceRef | None = None,
) -> bool:
    if ctx.is_admin:
        return True
    if permission in ctx.permissions:
        return True
    if resource is None:
        return False
    required_level = _grant_level_for_permission(permission)
    if required_level is None:
        return False
    owner_id = _resource_owner_user_id(conn, workspace_id=ctx.workspace_id, resource=resource)
    if owner_id == ctx.user_id:
        return True
    grant_level = _resource_grant_level(
        conn,
        workspace_id=ctx.workspace_id,
        resource=resource,
        grantee_user_id=ctx.user_id,
    )
    if grant_level and grant_level_covers(grant_level, required_level):
        return True
    return False


def can_manage_resource_grants(
    ctx: WorkspaceAuthContext,
    conn: Connection,
    *,
    resource: ResourceRef,
) -> bool:
    if ctx.is_admin:
        return True
    owner_id = _resource_owner_user_id(conn, workspace_id=ctx.workspace_id, resource=resource)
    if owner_id == ctx.user_id:
        return True
    grant_level = _resource_grant_level(
        conn,
        workspace_id=ctx.workspace_id,
        resource=resource,
        grantee_user_id=ctx.user_id,
    )
    return grant_level == "manage"


def create_resource_grant(
    conn: Connection,
    *,
    workspace_id: int,
    resource_type: str,
    resource_id: int,
    grantee_user_id: int,
    level: str,
    granted_by_user_id: int,
) -> dict[str, Any]:
    if level not in ("view", "edit", "manage"):
        raise ValueError("invalid grant level")
    if not is_workspace_member(conn, user_id=grantee_user_id, workspace_id=workspace_id):
        raise PermissionDenied("grantee not in workspace")
    row = conn.execute(
        text(
            """
            INSERT INTO resource_grant
              (workspace_id, resource_type, resource_id, grantee_user_id, level, granted_by_user_id)
            VALUES (:wid, :rt, :rid, :gid, :lvl, :by)
            ON CONFLICT ON CONSTRAINT uq_resource_grant_resource_grantee
            DO UPDATE SET level = EXCLUDED.level, granted_by_user_id = EXCLUDED.granted_by_user_id
            RETURNING id, workspace_id, resource_type, resource_id, grantee_user_id, level, granted_by_user_id, created_at
            """
        ),
        {
            "wid": workspace_id,
            "rt": resource_type,
            "rid": resource_id,
            "gid": grantee_user_id,
            "lvl": level,
            "by": granted_by_user_id,
        },
    ).mappings().one()
    return dict(row)


def delete_resource_grant(
    conn: Connection,
    *,
    workspace_id: int,
    resource_type: str,
    resource_id: int,
    grantee_user_id: int,
) -> bool:
    r = conn.execute(
        text(
            "DELETE FROM resource_grant "
            "WHERE workspace_id = :wid AND resource_type = :rt AND resource_id = :rid "
            "AND grantee_user_id = :gid RETURNING id"
        ),
        {
            "wid": workspace_id,
            "rt": resource_type,
            "rid": resource_id,
            "gid": grantee_user_id,
        },
    ).first()
    return r is not None


def list_resource_grants(
    conn: Connection,
    *,
    workspace_id: int,
    resource_type: str,
    resource_id: int,
) -> list[dict[str, Any]]:
    rows = conn.execute(
        text(
            """
            SELECT rg.id, rg.grantee_user_id, u.username AS grantee_username,
                   rg.level, rg.granted_by_user_id, gb.username AS granted_by_username, rg.created_at
            FROM resource_grant rg
            JOIN app_user u ON u.id = rg.grantee_user_id
            LEFT JOIN app_user gb ON gb.id = rg.granted_by_user_id
            WHERE rg.workspace_id = :wid AND rg.resource_type = :rt AND rg.resource_id = :rid
            ORDER BY rg.id
            """
        ),
        {"wid": workspace_id, "rt": resource_type, "rid": resource_id},
    ).mappings().all()
    return [dict(r) for r in rows]


def ensure_owner_manage_grant(
    conn: Connection,
    *,
    workspace_id: int,
    resource_type: str,
    resource_id: int,
    owner_user_id: int,
) -> None:
    create_resource_grant(
        conn,
        workspace_id=workspace_id,
        resource_type=resource_type,
        resource_id=resource_id,
        grantee_user_id=owner_user_id,
        level="manage",
        granted_by_user_id=owner_user_id,
    )


def _read_permission_for_type(resource_type: str) -> str:
    return f"{resource_type}.read"


def visible_resource_ids(
    conn: Connection,
    ctx: WorkspaceAuthContext,
    *,
    resource_type: str,
) -> set[int] | None:
    """None = все ресурсы типа в workspace видны; иначе только перечисленные id."""
    read_perm = _read_permission_for_type(resource_type)
    if ctx.is_admin or read_perm in ctx.permissions:
        return None
    rows = conn.execute(
        text(
            f"""
            SELECT id FROM {resource_type}
            WHERE workspace_id = :wid AND created_by_user_id = :uid
            UNION
            SELECT resource_id FROM resource_grant
            WHERE workspace_id = :wid AND resource_type = :rt AND grantee_user_id = :uid
            """
        ),
        {"wid": ctx.workspace_id, "uid": ctx.user_id, "rt": resource_type},
    ).fetchall()
    return {int(r[0]) for r in rows}


def filter_rows_by_visibility(
    ctx: WorkspaceAuthContext,
    conn: Connection,
    *,
    resource_type: str,
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    allowed = visible_resource_ids(conn, ctx, resource_type=resource_type)
    if allowed is None:
        return rows
    return [r for r in rows if int(r["id"]) in allowed]


def effective_permissions_for_user(
    conn: Connection, *, user_id: int, workspace_id: int
) -> tuple[bool, list[str]]:
    ctx = load_workspace_auth_context(conn, user_id=user_id, workspace_id=workspace_id)
    if ctx is None:
        return False, []
    if ctx.is_admin:
        from datanorma.web.permission_catalog import ALL_PERMISSION_CODES

        return True, list(ALL_PERMISSION_CODES)
    return False, sorted(ctx.permissions)
