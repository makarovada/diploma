"""Workspace ACL: permissions catalog, member permissions, resource grants.

Revision ID: 014_workspace_permissions_acl
Revises: 013_connection_stream_destination_sync_mode
Create Date: 2026-06-01
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "014_workspace_permissions_acl"
down_revision: Union[str, None] = "013_connection_stream_destination_sync_mode"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISSION_ROWS = [
    ("workspace.members.manage", "Управление участниками пространства", "workspace"),
    ("workspace.permissions.grant", "Выдача прав участникам", "workspace"),
    ("source.create", "Создание источников", "source"),
    ("source.read", "Просмотр источников", "source"),
    ("source.update", "Изменение источников", "source"),
    ("source.delete", "Удаление источников", "source"),
    ("destination.create", "Создание приёмников", "destination"),
    ("destination.read", "Просмотр приёмников", "destination"),
    ("destination.update", "Изменение приёмников", "destination"),
    ("destination.delete", "Удаление приёмников", "destination"),
    ("connection.create", "Создание подключений", "connection"),
    ("connection.read", "Просмотр подключений", "connection"),
    ("connection.update", "Изменение подключений", "connection"),
    ("connection.delete", "Удаление подключений", "connection"),
    ("connection.sync.run", "Запуск синхронизации", "connection"),
    ("mapping.read", "Просмотр профилей маппинга", "mapping"),
    ("mapping.edit", "Изменение профилей маппинга", "mapping"),
    ("audit.read", "Просмотр журнала аудита", "audit"),
]

INTEGRATOR_PERMS = [
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

ANALYST_PERMS = [
    "source.read",
    "destination.read",
    "connection.read",
    "mapping.read",
]


def _tables(bind) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


def _cols(bind, table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(bind).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()

    if "permission" not in _tables(bind):
        op.create_table(
            "permission",
            sa.Column("code", sa.String(64), primary_key=True),
            sa.Column("description_ru", sa.String(255), nullable=False),
            sa.Column("category", sa.String(32), nullable=False),
        )
    if "permission" in _tables(bind):
        for code, desc, cat in PERMISSION_ROWS:
            op.execute(
                sa.text(
                    "INSERT INTO permission (code, description_ru, category) VALUES (:c, :d, :cat) "
                    "ON CONFLICT (code) DO NOTHING"
                ).bindparams(c=code, d=desc, cat=cat),
            )

    if "workspace" in _tables(bind) and "created_by_user_id" not in _cols(bind, "workspace"):
        op.add_column(
            "workspace",
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("app_user.id", ondelete="SET NULL"), nullable=True),
        )

    if "user_workspace" in _tables(bind) and "is_admin" not in _cols(bind, "user_workspace"):
        op.add_column(
            "user_workspace",
            sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )

    if "workspace_member_permission" not in _tables(bind):
        op.create_table(
            "workspace_member_permission",
            sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspace.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("app_user.id", ondelete="CASCADE"), primary_key=True),
            sa.Column(
                "permission_code",
                sa.String(64),
                sa.ForeignKey("permission.code", ondelete="CASCADE"),
                primary_key=True,
            ),
        )
        op.create_index(
            "ix_workspace_member_permission_user",
            "workspace_member_permission",
            ["user_id", "workspace_id"],
            unique=False,
        )

    if "resource_grant" not in _tables(bind):
        op.create_table(
            "resource_grant",
            sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
            sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspace.id", ondelete="CASCADE"), nullable=False),
            sa.Column("resource_type", sa.String(32), nullable=False),
            sa.Column("resource_id", sa.BigInteger(), nullable=False),
            sa.Column("grantee_user_id", sa.Integer(), sa.ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False),
            sa.Column("level", sa.String(16), nullable=False),
            sa.Column("granted_by_user_id", sa.Integer(), sa.ForeignKey("app_user.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
            sa.UniqueConstraint(
                "workspace_id",
                "resource_type",
                "resource_id",
                "grantee_user_id",
                name="uq_resource_grant_resource_grantee",
            ),
        )
        op.create_index(
            "ix_resource_grant_lookup",
            "resource_grant",
            ["workspace_id", "resource_type", "resource_id", "grantee_user_id"],
            unique=False,
        )

    for table in ("source", "destination", "connection"):
        if table in _tables(bind) and "created_by_user_id" not in _cols(bind, table):
            op.add_column(
                table,
                sa.Column(
                    "created_by_user_id",
                    sa.Integer(),
                    sa.ForeignKey("app_user.id", ondelete="SET NULL"),
                    nullable=True,
                ),
            )
            op.execute(
                sa.text(
                    f"""
                    UPDATE {table} t
                    SET created_by_user_id = u.id
                    FROM app_user u
                    WHERE t.created_by IS NOT NULL
                      AND t.created_by = u.username
                      AND t.created_by_user_id IS NULL
                    """
                )
            )

    # First user in main workspace -> admin; set workspace.created_by if empty
    op.execute(
        sa.text(
            """
            UPDATE user_workspace uw
            SET is_admin = true
            FROM workspace w
            WHERE uw.workspace_id = w.id
              AND w.code = 'main'
              AND uw.user_id = (
                SELECT u.id FROM app_user u
                JOIN user_workspace uw2 ON uw2.user_id = u.id AND uw2.workspace_id = w.id
                ORDER BY u.id LIMIT 1
              )
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE workspace w
            SET created_by_user_id = (
                SELECT uw.user_id FROM user_workspace uw
                WHERE uw.workspace_id = w.id AND uw.is_admin = true
                ORDER BY uw.user_id LIMIT 1
            )
            WHERE w.created_by_user_id IS NULL
            """
        )
    )

    # Migrate legacy global roles -> workspace_member_permission on main workspace
    for perm in INTEGRATOR_PERMS:
        op.execute(
            sa.text(
                """
                INSERT INTO workspace_member_permission (workspace_id, user_id, permission_code)
                SELECT w.id, u.id, :perm
                FROM workspace w
                CROSS JOIN app_user u
                INNER JOIN user_role ur ON ur.user_id = u.id
                INNER JOIN role r ON r.id = ur.role_id AND r.name = 'data_integrator'
                WHERE w.code = 'main'
                ON CONFLICT DO NOTHING
                """
            ).bindparams(perm=perm),
        )
    for perm in ANALYST_PERMS:
        op.execute(
            sa.text(
                """
                INSERT INTO workspace_member_permission (workspace_id, user_id, permission_code)
                SELECT w.id, u.id, :perm
                FROM workspace w
                CROSS JOIN app_user u
                INNER JOIN user_role ur ON ur.user_id = u.id
                INNER JOIN role r ON r.id = ur.role_id AND r.name = 'analyst'
                WHERE w.code = 'main'
                ON CONFLICT DO NOTHING
                """
            ).bindparams(perm=perm),
        )
    op.execute(
        sa.text(
            """
            INSERT INTO workspace_member_permission (workspace_id, user_id, permission_code)
            SELECT w.id, u.id, p.code
            FROM workspace w
            CROSS JOIN app_user u
            INNER JOIN user_workspace uw ON uw.user_id = u.id AND uw.workspace_id = w.id AND uw.is_admin = true
            CROSS JOIN permission p
            WHERE w.code = 'main'
            ON CONFLICT DO NOTHING
            """
        )
    )

    # Implicit manage grants for resource owners
    for rtype, tbl in (("source", "source"), ("destination", "destination"), ("connection", "connection")):
        if tbl in _tables(bind):
            op.execute(
                sa.text(
                    f"""
                    INSERT INTO resource_grant
                      (workspace_id, resource_type, resource_id, grantee_user_id, level, granted_by_user_id)
                    SELECT t.workspace_id, :rtype, t.id, t.created_by_user_id, 'manage', t.created_by_user_id
                    FROM {tbl} t
                    WHERE t.created_by_user_id IS NOT NULL
                    ON CONFLICT ON CONSTRAINT uq_resource_grant_resource_grantee DO NOTHING
                    """
                ).bindparams(rtype=rtype),
            )

    # Globally unique workspace.code (if not already)
    if "workspace" in _tables(bind):
        op.execute(
            sa.text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'uq_workspace_code_global'
                    ) THEN
                        ALTER TABLE workspace ADD CONSTRAINT uq_workspace_code_global UNIQUE (code);
                    END IF;
                EXCEPTION
                    WHEN unique_violation THEN NULL;
                END $$;
                """
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    if "resource_grant" in _tables(bind):
        op.drop_table("resource_grant")
    if "workspace_member_permission" in _tables(bind):
        op.drop_table("workspace_member_permission")
    if "permission" in _tables(bind):
        op.drop_table("permission")
    for table in ("connection", "destination", "source"):
        if table in _tables(bind) and "created_by_user_id" in _cols(bind, table):
            op.drop_column(table, "created_by_user_id")
    if "user_workspace" in _tables(bind) and "is_admin" in _cols(bind, "user_workspace"):
        op.drop_column("user_workspace", "is_admin")
    if "workspace" in _tables(bind) and "created_by_user_id" in _cols(bind, "workspace"):
        op.drop_column("workspace", "created_by_user_id")
    if "workspace" in _tables(bind):
        op.execute(sa.text("ALTER TABLE workspace DROP CONSTRAINT IF EXISTS uq_workspace_code_global"))
