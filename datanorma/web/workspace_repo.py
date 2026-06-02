"""CRUD workspace и участников."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection


def list_workspaces_for_user(conn: Connection, *, user_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        text(
            """
            SELECT w.id, w.code, w.name, w.created_at, uw.is_admin,
                   w.created_by_user_id
            FROM user_workspace uw
            JOIN workspace w ON w.id = uw.workspace_id
            WHERE uw.user_id = :uid
            ORDER BY w.name, w.id
            """
        ),
        {"uid": user_id},
    ).mappings().all()
    return [dict(r) for r in rows]


def get_workspace(conn: Connection, *, workspace_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        text(
            "SELECT id, code, name, created_at, created_by_user_id FROM workspace WHERE id = :id"
        ),
        {"id": workspace_id},
    ).mappings().first()
    return dict(row) if row else None


def create_workspace(
    conn: Connection,
    *,
    code: str,
    name: str,
    created_by_user_id: int,
) -> dict[str, Any]:
    org_code = f"ws-{code}"
    conn.execute(
        text(
            "INSERT INTO organization(code, name) VALUES (:c, :n) "
            "ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name"
        ),
        {"c": org_code, "n": name.strip()},
    )
    row = conn.execute(
        text(
            """
            INSERT INTO workspace (organization_id, code, name, created_by_user_id, created_at)
            SELECT o.id, :wc, :wn, :uid, NOW()
            FROM organization o WHERE o.code = :oc
            ON CONFLICT ON CONSTRAINT uq_workspace_org_code
            DO UPDATE SET name = EXCLUDED.name
            RETURNING id, code, name, created_at, created_by_user_id
            """
        ),
        {"oc": org_code, "wc": code.strip(), "wn": name.strip(), "uid": created_by_user_id},
    ).mappings().one()
    wid = int(row["id"])
    conn.execute(
        text(
            "INSERT INTO user_workspace (user_id, workspace_id, is_admin) "
            "VALUES (:uid, :wid, true) ON CONFLICT (user_id, workspace_id) "
            "DO UPDATE SET is_admin = true"
        ),
        {"uid": created_by_user_id, "wid": wid},
    )
    return dict(row)


def list_workspace_members(conn: Connection, *, workspace_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        text(
            """
            SELECT u.id AS user_id, u.username, u.email, uw.is_admin, uw.created_at AS joined_at
            FROM user_workspace uw
            JOIN app_user u ON u.id = uw.user_id
            WHERE uw.workspace_id = :wid
            ORDER BY uw.is_admin DESC, u.username
            """
        ),
        {"wid": workspace_id},
    ).mappings().all()
    return [dict(r) for r in rows]


def add_workspace_member(
    conn: Connection,
    *,
    workspace_id: int,
    user_id: int,
    is_admin: bool = False,
) -> None:
    conn.execute(
        text(
            "INSERT INTO user_workspace (user_id, workspace_id, is_admin) "
            "VALUES (:uid, :wid, :adm) ON CONFLICT (user_id, workspace_id) DO NOTHING"
        ),
        {"uid": user_id, "wid": workspace_id, "adm": is_admin},
    )


def remove_workspace_member(conn: Connection, *, workspace_id: int, user_id: int) -> bool:
    admin_count = conn.execute(
        text(
            "SELECT COUNT(*) FROM user_workspace WHERE workspace_id = :wid AND is_admin = true"
        ),
        {"wid": workspace_id},
    ).scalar_one()
    is_target_admin = conn.execute(
        text(
            "SELECT is_admin FROM user_workspace WHERE workspace_id = :wid AND user_id = :uid"
        ),
        {"wid": workspace_id, "uid": user_id},
    ).scalar()
    if is_target_admin and int(admin_count) <= 1:
        raise ValueError("last_admin")
    r = conn.execute(
        text(
            "DELETE FROM user_workspace WHERE workspace_id = :wid AND user_id = :uid RETURNING user_id"
        ),
        {"wid": workspace_id, "uid": user_id},
    ).first()
    if r is not None:
        conn.execute(
            text(
                "DELETE FROM workspace_member_permission WHERE workspace_id = :wid AND user_id = :uid"
            ),
            {"wid": workspace_id, "uid": user_id},
        )
    return r is not None


def find_user_id_by_username(conn: Connection, username: str) -> int | None:
    row = conn.execute(
        text("SELECT id FROM app_user WHERE username = :u AND COALESCE(is_active, true)"),
        {"u": username.strip()},
    ).mappings().first()
    return int(row["id"]) if row else None


def count_workspace_admins(conn: Connection, *, workspace_id: int) -> int:
    return int(
        conn.execute(
            text(
                "SELECT COUNT(*) FROM user_workspace WHERE workspace_id = :wid AND is_admin = true"
            ),
            {"wid": workspace_id},
        ).scalar_one()
    )
