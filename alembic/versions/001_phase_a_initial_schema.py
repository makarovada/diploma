"""Фаза А: справочники, raw staging, витрина, пользователи/роли, аудит нормализации.

Revision ID: 001_phase_a
Revises:
Create Date: 2026-03-29

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_phase_a"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_names(bind) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


def _column_names(bind, table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(bind).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()

    if "dim_source_system" not in _table_names(bind):
        op.create_table(
        "dim_source_system",
        sa.Column("code", sa.String(32), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
    )
    if "dim_currency" not in _table_names(bind):
        op.create_table(
        "dim_currency",
        sa.Column("code", sa.String(8), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
    )
    if "role" not in _table_names(bind):
        op.create_table(
        "role",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("name", sa.String(64), nullable=False, unique=True),
        sa.Column("description", sa.Text()),
    )
    if "app_user" not in _table_names(bind):
        op.create_table(
        "app_user",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("username", sa.String(128), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    if "user_role" not in _table_names(bind):
        op.create_table(
        "user_role",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("app_user.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("role.id", ondelete="CASCADE"), primary_key=True),
    )
    if "integration_config" not in _table_names(bind):
        op.create_table(
        "integration_config",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("config_key", sa.String(128), nullable=False),
        sa.Column("config_value", sa.Text()),
        sa.Column("is_secret", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    if "mapping_profile" not in _table_names(bind):
        op.create_table(
        "mapping_profile",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1")),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    if "canonical_sales" not in _table_names(bind):
        op.create_table(
            "canonical_sales",
            sa.Column("source_system", sa.String(64), nullable=False),
            sa.Column("source_record_id", sa.String(512), nullable=False),
            sa.Column("event_datetime", sa.DateTime(timezone=True)),
            sa.Column("amount", sa.Numeric(18, 4)),
            sa.Column("amount_rub", sa.Numeric(18, 4)),
            sa.Column("currency_code", sa.String(16)),
            sa.Column("counterparty_name", sa.Text()),
            sa.Column("channel", sa.String(128)),
            sa.Column("line_description", sa.Text()),
            sa.Column("status", sa.String(128)),
            sa.Column("cbr_rate_date", sa.Date()),
            sa.Column("line_unit_normalized", sa.String(64)),
            sa.Column("normalization_meta", postgresql.JSONB()),
            sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
            sa.PrimaryKeyConstraint("source_system", "source_record_id"),
        )
    elif "normalization_meta" not in _column_names(bind, "canonical_sales"):
        op.add_column(
            "canonical_sales",
            sa.Column("normalization_meta", postgresql.JSONB(), nullable=True),
        )
    if "raw_ozon_staging" not in _table_names(bind):
        op.create_table(
        "raw_ozon_staging",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("ingest_batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    if "raw_1c_staging" not in _table_names(bind):
        op.create_table(
        "raw_1c_staging",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("ingest_batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("row_json", postgresql.JSONB(), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    if "raw_sheet_staging" not in _table_names(bind):
        op.create_table(
        "raw_sheet_staging",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("ingest_batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("row_json", postgresql.JSONB(), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    if "normalization_issue" not in _table_names(bind):
        op.create_table(
        "normalization_issue",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True)),
        sa.Column("source_system", sa.String(64)),
        sa.Column("source_record_id", sa.String(512)),
        sa.Column("field_name", sa.String(128)),
        sa.Column("issue_type", sa.String(64), nullable=False),
        sa.Column("message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    if "sync_state" not in _table_names(bind):
        op.create_table(
        "sync_state",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("integration_code", sa.String(64), nullable=False, unique=True),
        sa.Column("cursor_value", sa.Text()),
        sa.Column("last_success_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    if "pipeline_run_summary" not in _table_names(bind):
        op.create_table(
        "pipeline_run_summary",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("dagster_run_id", sa.String(128)),
        sa.Column("job_name", sa.String(128)),
        sa.Column("status", sa.String(32)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("meta", postgresql.JSONB()),
    )


def downgrade() -> None:
    # IF EXISTS: безопасно при частично применённых миграциях и не ломается на «чужих» объектах.
    order = (
        "pipeline_run_summary",
        "sync_state",
        "normalization_issue",
        "raw_sheet_staging",
        "raw_1c_staging",
        "raw_ozon_staging",
        "canonical_sales",
        "mapping_profile",
        "integration_config",
        "user_role",
        "app_user",
        "role",
        "dim_currency",
        "dim_source_system",
    )
    for t in order:
        op.execute(sa.text(f'DROP TABLE IF EXISTS "{t}" CASCADE'))
