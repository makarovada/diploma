"""Phase 10: workspace_id on sync_run, sync_state, normalization_issue, sync_run_log, integration_config;
    optional per-workspace roles on user_workspace.

Revision ID: 010_phase10_workspace_tenant_columns
Revises: 8d7cc11a83b1
Create Date: 2026-05-03
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "010_phase10_workspace_tenant_columns"
down_revision: Union[str, None] = "8d7cc11a83b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables(bind) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


def _cols(bind, table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(bind).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()

    if "user_workspace" in _tables(bind) and "roles_override" not in _cols(bind, "user_workspace"):
        op.add_column(
            "user_workspace",
            sa.Column("roles_override", postgresql.JSONB(), nullable=True),
        )

    main_wid_sql = "(SELECT w.id FROM workspace w WHERE w.code = 'main' ORDER BY w.id LIMIT 1)"

    if "sync_run" in _tables(bind) and "workspace_id" not in _cols(bind, "sync_run"):
        op.add_column(
            "sync_run",
            sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspace.id", ondelete="SET NULL"), nullable=True),
        )
        op.create_index("ix_sync_run_workspace_id", "sync_run", ["workspace_id"], unique=False)
        op.execute(
            sa.text(
                f"""
                UPDATE sync_run sr
                SET workspace_id = c.workspace_id
                FROM connection c
                WHERE sr.domain_connection_id = c.id AND sr.workspace_id IS NULL
                """
            )
        )
        op.execute(sa.text(f"UPDATE sync_run SET workspace_id = {main_wid_sql} WHERE workspace_id IS NULL"))

    if "sync_state" in _tables(bind) and "workspace_id" not in _cols(bind, "sync_state"):
        op.add_column(
            "sync_state",
            sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspace.id", ondelete="SET NULL"), nullable=True),
        )
        op.create_index("ix_sync_state_workspace_id", "sync_state", ["workspace_id"], unique=False)
        op.execute(
            sa.text(
                """
                UPDATE sync_state ss
                SET workspace_id = c.workspace_id
                FROM connection_stream cs
                JOIN connection c ON c.id = cs.connection_id
                WHERE ss.connection_stream_id = cs.id AND ss.workspace_id IS NULL
                """
            )
        )
        op.execute(sa.text(f"UPDATE sync_state SET workspace_id = {main_wid_sql} WHERE workspace_id IS NULL"))

    if "normalization_issue" in _tables(bind) and "workspace_id" not in _cols(bind, "normalization_issue"):
        op.add_column(
            "normalization_issue",
            sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspace.id", ondelete="SET NULL"), nullable=True),
        )
        op.create_index("ix_normalization_issue_workspace_id", "normalization_issue", ["workspace_id"], unique=False)
        op.execute(sa.text(f"UPDATE normalization_issue SET workspace_id = {main_wid_sql} WHERE workspace_id IS NULL"))

    if "sync_run_log" in _tables(bind) and "workspace_id" not in _cols(bind, "sync_run_log"):
        op.add_column(
            "sync_run_log",
            sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspace.id", ondelete="SET NULL"), nullable=True),
        )
        op.create_index("ix_sync_run_log_workspace_id", "sync_run_log", ["workspace_id"], unique=False)
        op.execute(
            sa.text(
                """
                UPDATE sync_run_log sl
                SET workspace_id = sr.workspace_id
                FROM sync_run sr
                WHERE sl.sync_run_id = sr.id AND sl.workspace_id IS NULL
                """
            )
        )
        op.execute(sa.text(f"UPDATE sync_run_log SET workspace_id = {main_wid_sql} WHERE workspace_id IS NULL"))

    if "integration_config" in _tables(bind) and "workspace_id" not in _cols(bind, "integration_config"):
        op.add_column(
            "integration_config",
            sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspace.id", ondelete="CASCADE"), nullable=True),
        )
        op.create_index("ix_integration_config_workspace_id", "integration_config", ["workspace_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    if "integration_config" in _tables(bind) and "workspace_id" in _cols(bind, "integration_config"):
        op.drop_index("ix_integration_config_workspace_id", table_name="integration_config")
        op.drop_column("integration_config", "workspace_id")
    if "sync_run_log" in _tables(bind) and "workspace_id" in _cols(bind, "sync_run_log"):
        op.drop_index("ix_sync_run_log_workspace_id", table_name="sync_run_log")
        op.drop_column("sync_run_log", "workspace_id")
    if "normalization_issue" in _tables(bind) and "workspace_id" in _cols(bind, "normalization_issue"):
        op.drop_index("ix_normalization_issue_workspace_id", table_name="normalization_issue")
        op.drop_column("normalization_issue", "workspace_id")
    if "sync_state" in _tables(bind) and "workspace_id" in _cols(bind, "sync_state"):
        op.drop_index("ix_sync_state_workspace_id", table_name="sync_state")
        op.drop_column("sync_state", "workspace_id")
    if "sync_run" in _tables(bind) and "workspace_id" in _cols(bind, "sync_run"):
        op.drop_index("ix_sync_run_workspace_id", table_name="sync_run")
        op.drop_column("sync_run", "workspace_id")
    if "user_workspace" in _tables(bind) and "roles_override" in _cols(bind, "user_workspace"):
        op.drop_column("user_workspace", "roles_override")
