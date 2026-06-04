"""Привести normalization_issue к ELT-схеме (012), если осталась legacy-таблица Phase 1.

Revision ID: 016_elt_normalization_issue_schema
Revises: 015_sync_state_per_connection_stream
Create Date: 2026-06-04
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "016_elt_normalization_issue_schema"
down_revision: Union[str, None] = "015_sync_state_per_connection_stream"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables(bind) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


def _cols(bind, table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(bind).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    tables = _tables(bind)
    if "normalization_issue" not in tables:
        op.create_table(
            "normalization_issue",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("sync_run_id", sa.BigInteger(), sa.ForeignKey("sync_run.id", ondelete="CASCADE"), nullable=False),
            sa.Column("connection_id", sa.BigInteger(), nullable=False),
            sa.Column("stream_name", sa.Text(), nullable=False),
            sa.Column("source_record_id", sa.Text(), nullable=True),
            sa.Column("target_field", sa.Text(), nullable=True),
            sa.Column("error_code", sa.Text(), nullable=False),
            sa.Column("error_text", sa.Text(), nullable=True),
            sa.Column("raw_value", postgresql.JSONB(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        )
        op.create_index("ix_normalization_issue_run", "normalization_issue", ["sync_run_id"], unique=False)
        return

    cols = _cols(bind, "normalization_issue")
    if "sync_run_id" in cols:
        return

    op.execute(sa.text("DROP INDEX IF EXISTS ix_normalization_issue_workspace_id"))
    op.execute(sa.text("ALTER TABLE normalization_issue DROP CONSTRAINT IF EXISTS ck_normalization_issue_status"))
    op.execute(sa.text("ALTER TABLE normalization_issue DROP CONSTRAINT IF EXISTS normalization_issue_workspace_id_fkey"))
    op.drop_table("normalization_issue")
    op.create_table(
        "normalization_issue",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("sync_run_id", sa.BigInteger(), sa.ForeignKey("sync_run.id", ondelete="CASCADE"), nullable=False),
        sa.Column("connection_id", sa.BigInteger(), nullable=False),
        sa.Column("stream_name", sa.Text(), nullable=False),
        sa.Column("source_record_id", sa.Text(), nullable=True),
        sa.Column("target_field", sa.Text(), nullable=True),
        sa.Column("error_code", sa.Text(), nullable=False),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.Column("raw_value", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_normalization_issue_run", "normalization_issue", ["sync_run_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    tables = _tables(bind)
    if "normalization_issue" not in tables:
        return
    cols = _cols(bind, "normalization_issue")
    if "sync_run_id" not in cols:
        return
    op.drop_index("ix_normalization_issue_run", table_name="normalization_issue")
    op.drop_table("normalization_issue")
