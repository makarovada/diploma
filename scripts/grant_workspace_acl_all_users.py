"""Выдать workspace-доступ всем существующим пользователям.

Используется для починки 403 `Нет доступа к workspace` в UI при выборе "текущего" workspace.

Скрипт:
- не очищает данные
- добавляет `user_workspace` (membership) для каждого `app_user` на каждый `workspace`
- `seed_admin` получает `user_workspace.is_admin = true` (права создателя)
- для non-admin пользователей проставляет `workspace_member_permission` по глобальным ролям:
  - `data_integrator` -> расширенный набор connection/source/destination/mapping
  - `analyst` -> read-only набор
"""

from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection

from datanorma.config import get_settings


def _grant_workspace_acl_for_all_workspaces(conn: Connection) -> None:
    seed_admin_uid = conn.execute(
        text("SELECT id FROM app_user WHERE username = 'seed_admin'")
    ).scalar()
    if seed_admin_uid is None:
        return

    workspace_ids = conn.execute(text("SELECT id FROM workspace")).scalars().all()
    if not workspace_ids:
        return

    # 1) Membership: для всех app_user на все workspaces.
    conn.execute(
        text(
            """
            INSERT INTO user_workspace (user_id, workspace_id, is_admin)
            SELECT u.id,
                   w.id,
                   (u.id = :seed_uid) AS is_admin
            FROM app_user u
            CROSS JOIN workspace w
            ON CONFLICT (user_id, workspace_id)
            DO UPDATE SET is_admin = user_workspace.is_admin OR EXCLUDED.is_admin
            """
        ),
        {"seed_uid": int(seed_admin_uid)},
    )

    # 2) Permissions: для non-admin пользователей.
    integrator_perms = [
        "source.create",
        "source.read",
        "source.update",
        "source.delete",
        "destination.create",
        "destination.read",
        "destination.update",
        "destination.delete",
        "connection.create",
        "connection.read",
        "connection.update",
        "connection.delete",
        "connection.sync.run",
        "mapping.read",
        "mapping.edit",
    ]
    analyst_perms = [
        "source.read",
        "destination.read",
        "connection.read",
        "mapping.read",
    ]

    user_role_rows = conn.execute(
        text(
            """
            SELECT ur.user_id, r.name
            FROM user_role ur
            JOIN role r ON r.id = ur.role_id
            """
        )
    ).all()
    roles_by_user: dict[int, set[str]] = {}
    for user_id, role_name in user_role_rows:
        roles_by_user.setdefault(int(user_id), set()).add(str(role_name))

    for wid in workspace_ids:
        for user_id, roles in roles_by_user.items():
            if user_id == int(seed_admin_uid):
                continue
            perm_codes: set[str] = set()
            if "data_integrator" in roles:
                perm_codes.update(integrator_perms)
            if "analyst" in roles:
                perm_codes.update(analyst_perms)
            if not perm_codes:
                continue
            for p in perm_codes:
                conn.execute(
                    text(
                        """
                        INSERT INTO workspace_member_permission (workspace_id, user_id, permission_code)
                        VALUES (:w, :u, :p)
                        ON CONFLICT DO NOTHING
                        """
                    ),
                    {"w": int(wid), "u": int(user_id), "p": p},
                )


def main() -> None:
    engine = create_engine(get_settings().database_url, pool_pre_ping=True)
    with engine.begin() as conn:
        _grant_workspace_acl_for_all_workspaces(conn)
    print("Workspace ACL granted OK")


if __name__ == "__main__":
    main()

