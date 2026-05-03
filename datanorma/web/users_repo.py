"""Загрузка пользователя и ролей из PostgreSQL."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection


@dataclass
class DbUser:
    id: int
    username: str
    email: str | None
    password_hash: str
    roles: list[str]


def update_user_password_hash(conn: Connection, user_id: int, password_hash: str) -> None:
    conn.execute(
        text("UPDATE app_user SET password_hash = :h WHERE id = :id"),
        {"h": password_hash, "id": user_id},
    )


def load_user_by_username(conn: Connection, username: str) -> DbUser | None:
    urow = conn.execute(
        text(
            "SELECT id, username, email, password_hash FROM app_user "
            "WHERE username = :u AND COALESCE(is_active, true)"
        ),
        {"u": username.strip()},
    ).mappings().first()
    if urow is None:
        return None
    uid = int(urow["id"])
    role_rows = conn.execute(
        text("SELECT r.name FROM role r INNER JOIN user_role ur ON ur.role_id = r.id WHERE ur.user_id = :id"),
        {"id": uid},
    ).fetchall()
    roles = [str(r[0]) for r in role_rows]
    return DbUser(
        id=uid,
        username=str(urow["username"]),
        email=str(urow["email"]) if urow.get("email") else None,
        password_hash=str(urow["password_hash"]),
        roles=roles,
    )


def list_users_with_roles(conn: Connection) -> list[dict[str, Any]]:
    users: dict[int, dict[str, Any]] = {}
    for row in conn.execute(
        text(
            "SELECT u.id, u.username, u.email, r.name AS role_name "
            "FROM app_user u "
            "LEFT JOIN user_role ur ON ur.user_id = u.id "
            "LEFT JOIN role r ON r.id = ur.role_id "
            "ORDER BY u.id, r.name"
        )
    ).mappings():
        uid = int(row["id"])
        if uid not in users:
            users[uid] = {
                "id": uid,
                "username": row["username"],
                "email": row["email"],
                "roles": [],
            }
        rn = row.get("role_name")
        if rn:
            users[uid]["roles"].append(str(rn))
    return list(users.values())


def list_roles(conn: Connection) -> list[dict[str, Any]]:
    return [
        {"id": int(r[0]), "name": str(r[1]), "description": r[2]}
        for r in conn.execute(text("SELECT id, name, description FROM role ORDER BY id"))
    ]
