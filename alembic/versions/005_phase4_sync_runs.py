"""Phase 4: sync_run lifecycle table for UI/API-triggered sync orchestration.

Revision ID: 005_phase4_sync_runs
Revises: 004_phase3_multitenancy
Create Date: 2026-05-01
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005_phase4_sync_runs"
down_revision: Union[str, None] = "004_phase3_multitenancy"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables(bind) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


def _cols(bind, table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(bind).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    if "sync_run" not in _tables(bind):
        op.create_table(
            "sync_run",
            sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
            sa.Column("connection_id", sa.Integer(), sa.ForeignKey("sync_state.id", ondelete="SET NULL"), nullable=True),
            sa.Column("integration_code", sa.String(64), nullable=True),
            sa.Column("stream_name", sa.String(128), nullable=True),
            sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'queued'")),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("triggered_by", sa.String(128), nullable=False),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("dagster_run_id", sa.String(128), nullable=True),
            sa.Column("meta", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
            sa.CheckConstraint(
                "status IN ('queued', 'running', 'success', 'failed', 'cancelled')",
                name="ck_sync_run_status",
            ),
        )
        op.create_index("ix_sync_run_connection_id", "sync_run", ["connection_id"], unique=False)
        op.create_index("ix_sync_run_status", "sync_run", ["status"], unique=False)
        op.create_index("ix_sync_run_created_at", "sync_run", ["created_at"], unique=False)
        op.create_index("ix_sync_run_dagster_run_id", "sync_run", ["dagster_run_id"], unique=False)
        return

    cols = _cols(bind, "sync_run")
    if "connection_id" not in cols:
        op.add_column("sync_run", sa.Column("connection_id", sa.Integer(), nullable=True))
    if "integration_code" not in cols:
        op.add_column("sync_run", sa.Column("integration_code", sa.String(64), nullable=True))
    if "stream_name" not in cols:
        op.add_column("sync_run", sa.Column("stream_name", sa.String(128), nullable=True))
    if "triggered_by" not in cols:
        op.add_column("sync_run", sa.Column("triggered_by", sa.String(128), nullable=False, server_default=sa.text("'system'")))
    if "error_message" not in cols:
        op.add_column("sync_run", sa.Column("error_message", sa.Text(), nullable=True))
    if "meta" not in cols:
        op.add_column("sync_run", sa.Column("meta", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")))
    if "created_at" not in cols:
        op.add_column("sync_run", sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")))
    if "updated_at" not in cols:
        op.add_column("sync_run", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")))

    op.execute(sa.text("ALTER TABLE sync_run DROP CONSTRAINT IF EXISTS ck_sync_run_status"))
    op.execute(
        sa.text(
            "ALTER TABLE sync_run ADD CONSTRAINT ck_sync_run_status "
            "CHECK (status IN ('queued', 'running', 'success', 'failed', 'cancelled'))"
        )
    )
    op.execute(
        sa.text(
            "DO $$ BEGIN "
            "IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_sync_run_connection_id_sync_state') THEN "
            "ALTER TABLE sync_run ADD CONSTRAINT fk_sync_run_connection_id_sync_state "
            "FOREIGN KEY (connection_id) REFERENCES sync_state(id) ON DELETE SET NULL; "
            "END IF; END $$;"
        )
    )
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_sync_run_connection_id ON sync_run (connection_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_sync_run_status ON sync_run (status)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_sync_run_created_at ON sync_run (created_at)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_sync_run_dagster_run_id ON sync_run (dagster_run_id)"))


def downgrade() -> None:
    bind = op.get_bind()
    if "sync_run" in _tables(bind):
        op.drop_index("ix_sync_run_dagster_run_id", table_name="sync_run")
        op.drop_index("ix_sync_run_created_at", table_name="sync_run")
        op.drop_index("ix_sync_run_status", table_name="sync_run")
        op.drop_index("ix_sync_run_connection_id", table_name="sync_run")
        op.drop_table("sync_run")
