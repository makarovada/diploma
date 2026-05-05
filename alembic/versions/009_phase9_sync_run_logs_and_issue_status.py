"""Phase 9: sync_run_log table and issue status actions.

Revision ID: 009_phase9_sync_run_logs_and_issue_status
Revises: 008_phase4_source_destination_connection
Create Date: 2026-05-03
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "009_phase9_sync_run_logs_and_issue_status"
down_revision: Union[str, None] = "008_phase4_source_destination_connection"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables(bind) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


def _cols(bind, table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(bind).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()

    if "sync_run_log" not in _tables(bind):
        op.create_table(
            "sync_run_log",
            sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
            sa.Column("sync_run_id", sa.BigInteger(), sa.ForeignKey("sync_run.id", ondelete="CASCADE"), nullable=False),
            sa.Column("stage", sa.String(32), nullable=False),
            sa.Column("level", sa.String(16), nullable=False, server_default=sa.text("'info'")),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("technical_details", postgresql.JSONB(), nullable=True),
            sa.Column("record_ref", sa.String(512), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        )
        op.create_index("ix_sync_run_log_sync_run_id", "sync_run_log", ["sync_run_id"], unique=False)
        op.create_index("ix_sync_run_log_created_at", "sync_run_log", ["created_at"], unique=False)

    if "normalization_issue" in _tables(bind):
        cols = _cols(bind, "normalization_issue")
        if "status" not in cols:
            op.add_column(
                "normalization_issue",
                sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'open'")),
            )
        if "resolved_at" not in cols:
            op.add_column("normalization_issue", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True))
        if "resolution_note" not in cols:
            op.add_column("normalization_issue", sa.Column("resolution_note", sa.Text(), nullable=True))
        if "resolved_by" not in cols:
            op.add_column("normalization_issue", sa.Column("resolved_by", sa.String(128), nullable=True))
        op.execute(sa.text("ALTER TABLE normalization_issue DROP CONSTRAINT IF EXISTS ck_normalization_issue_status"))
        op.execute(
            sa.text(
                "ALTER TABLE normalization_issue ADD CONSTRAINT ck_normalization_issue_status "
                "CHECK (status IN ('open', 'resolved', 'ignored'))"
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    if "normalization_issue" in _tables(bind):
        cols = _cols(bind, "normalization_issue")
        if "resolved_by" in cols:
            op.drop_column("normalization_issue", "resolved_by")
        if "resolution_note" in cols:
            op.drop_column("normalization_issue", "resolution_note")
        if "resolved_at" in cols:
            op.drop_column("normalization_issue", "resolved_at")
        if "status" in cols:
            op.drop_column("normalization_issue", "status")
    if "sync_run_log" in _tables(bind):
        op.drop_index("ix_sync_run_log_created_at", table_name="sync_run_log")
        op.drop_index("ix_sync_run_log_sync_run_id", table_name="sync_run_log")
        op.drop_table("sync_run_log")
