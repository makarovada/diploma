"""Phase 12: drop canonical tables, add stream rules and issues storage.

Revision ID: 012_drop_canonical_add_rules
Revises: 011_phase11_audit_log
Create Date: 2026-05-05
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "012_drop_canonical_add_rules"
down_revision: Union[str, None] = "011_phase11_audit_log"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables(bind) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


def _has_column(bind, table_name: str, col_name: str) -> bool:
    cols = sa.inspect(bind).get_columns(table_name)
    return any(c["name"] == col_name for c in cols)


def upgrade() -> None:
    bind = op.get_bind()
    tables = _tables(bind)

    if "typed_canonical_sales" in tables:
        op.drop_table("typed_canonical_sales")
    if "canonical_marketing_events" in tables:
        op.drop_table("canonical_marketing_events")

    if "connection_stream_rules" not in tables:
        op.create_table(
            "connection_stream_rules",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("connection_id", sa.BigInteger(), sa.ForeignKey("connection.id", ondelete="CASCADE"), nullable=False),
            sa.Column("stream_name", sa.Text(), nullable=False),
            sa.Column("sync_mode", sa.Text(), nullable=False, server_default="full_refresh"),
            sa.Column("cursor_field", sa.Text(), nullable=True),
            sa.Column("primary_key", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
            sa.Column("drop_unknown_columns", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
            sa.Column("deduplicate", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
            sa.UniqueConstraint("connection_id", "stream_name", name="uq_connection_stream_rules_conn_stream"),
        )

    if "connection_column_rule" not in tables:
        op.create_table(
            "connection_column_rule",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("stream_rules_id", sa.BigInteger(), sa.ForeignKey("connection_stream_rules.id", ondelete="CASCADE"), nullable=False),
            sa.Column("source_field", sa.Text(), nullable=False),
            sa.Column("target_field", sa.Text(), nullable=False),
            sa.Column("type", sa.Text(), nullable=False),
            sa.Column("nullable", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
            sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
            sa.Column("params", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("on_error", sa.Text(), nullable=False, server_default="null"),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("description", sa.Text(), nullable=True),
            sa.UniqueConstraint("stream_rules_id", "target_field", name="uq_connection_column_rule_stream_target"),
        )

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

    if "normalized_table_meta" not in tables:
        op.create_table(
            "normalized_table_meta",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("connection_id", sa.BigInteger(), nullable=False),
            sa.Column("stream_name", sa.Text(), nullable=False),
            sa.Column("schema_name", sa.Text(), nullable=False, server_default="normalized"),
            sa.Column("table_name", sa.Text(), nullable=False),
            sa.Column("columns", postgresql.JSONB(), nullable=False),
            sa.Column("last_evolved_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
            sa.UniqueConstraint("connection_id", "stream_name", name="uq_normalized_table_meta_conn_stream"),
        )

    if _has_column(bind, "connection", "wizard_meta") is False:
        op.add_column("connection", sa.Column("wizard_meta", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    tables = _tables(bind)

    if _has_column(bind, "connection", "wizard_meta"):
        op.drop_column("connection", "wizard_meta")

    if "normalized_table_meta" in tables:
        op.drop_table("normalized_table_meta")
    if "normalization_issue" in tables:
        op.drop_index("ix_normalization_issue_run", table_name="normalization_issue")
        op.drop_table("normalization_issue")
    if "connection_column_rule" in tables:
        op.drop_table("connection_column_rule")
    if "connection_stream_rules" in tables:
        op.drop_table("connection_stream_rules")

    if "typed_canonical_sales" not in tables:
        op.create_table(
            "typed_canonical_sales",
            sa.Column("source_system", sa.String(length=64), nullable=False),
            sa.Column("source_record_id", sa.String(length=512), nullable=False),
            sa.Column("event_datetime", sa.DateTime(timezone=True), nullable=True),
            sa.Column("amount", sa.Numeric(18, 4), nullable=True),
            sa.Column("amount_rub", sa.Numeric(18, 4), nullable=True),
            sa.Column("currency_code", sa.String(length=16), nullable=True),
            sa.Column("counterparty_name", sa.Text(), nullable=True),
            sa.Column("channel", sa.String(length=128), nullable=True),
            sa.Column("line_description", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=128), nullable=True),
            sa.Column("line_unit_normalized", sa.String(length=64), nullable=True),
            sa.Column("cbr_rate_date", sa.Date(), nullable=True),
            sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
            sa.PrimaryKeyConstraint("source_system", "source_record_id", name="pk_typed_canonical_sales"),
        )
