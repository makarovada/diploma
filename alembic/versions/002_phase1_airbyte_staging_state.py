"""Phase 1: Airbyte-style raw staging names, _airbyte_* meta columns, sync_state per stream, warehouse _airbyte_loaded_at.

Revision ID: 002_phase1_airbyte
Revises: 001_phase_a
Create Date: 2026-03-29

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002_phase1_airbyte"
down_revision: Union[str, None] = "001_phase_a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables(bind) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


def _cols(bind, table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(bind).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    t = _tables(bind)

    # --- rename raw_* → raw_<source>_<stream>_staging ---
    if "raw_ozon_staging" in t and "raw_ozon_postings_staging" not in t:
        op.rename_table("raw_ozon_staging", "raw_ozon_postings_staging")
    if "raw_1c_staging" in t and "raw_1c_orders_staging" not in t:
        op.rename_table("raw_1c_staging", "raw_1c_orders_staging")
    if "raw_sheet_staging" in t and "raw_google_sheet_orders_staging" not in t:
        op.rename_table("raw_sheet_staging", "raw_google_sheet_orders_staging")

    t = _tables(bind)
    staging_tables = [
        "raw_ozon_postings_staging",
        "raw_1c_orders_staging",
        "raw_google_sheet_orders_staging",
    ]
    for tbl in staging_tables:
        if tbl not in t:
            continue
        c = _cols(bind, tbl)
        if "_airbyte_raw_id" not in c:
            op.add_column(
                tbl,
                sa.Column(
                    "_airbyte_raw_id",
                    postgresql.UUID(as_uuid=True),
                    server_default=sa.text("gen_random_uuid()"),
                    nullable=False,
                ),
            )
        if "_airbyte_extracted_at" not in c:
            op.add_column(
                tbl,
                sa.Column(
                    "_airbyte_extracted_at",
                    sa.DateTime(timezone=True),
                    nullable=False,
                    server_default=sa.text("NOW()"),
                ),
            )
        if "_airbyte_meta" not in c:
            op.add_column(
                tbl,
                sa.Column(
                    "_airbyte_meta",
                    postgresql.JSONB(),
                    nullable=False,
                    server_default=sa.text("'{}'::jsonb"),
                ),
            )

    # --- sync_state: per-stream + Airbyte state ---
    if "sync_state" in _tables(bind):
        op.execute(sa.text("ALTER TABLE sync_state DROP CONSTRAINT IF EXISTS sync_state_integration_code_key"))
        if "stream_name" not in _cols(bind, "sync_state"):
            op.add_column("sync_state", sa.Column("stream_name", sa.String(64), nullable=True))
            op.execute(
                sa.text(
                    "UPDATE sync_state SET stream_name = CASE integration_code "
                    "WHEN 'ozon' THEN 'postings' "
                    "WHEN '1c' THEN 'orders' "
                    "WHEN 'google_sheet' THEN 'orders' "
                    "ELSE 'default' END"
                )
            )
            op.alter_column("sync_state", "stream_name", nullable=False)
        if "sync_mode" not in _cols(bind, "sync_state"):
            op.add_column(
                "sync_state",
                sa.Column(
                    "sync_mode",
                    sa.String(32),
                    nullable=False,
                    server_default=sa.text("'full_refresh'"),
                ),
            )
        if "cursor_field" not in _cols(bind, "sync_state"):
            op.add_column("sync_state", sa.Column("cursor_field", sa.String(256), nullable=True))
        if "airbyte_state" not in _cols(bind, "sync_state"):
            op.add_column("sync_state", sa.Column("airbyte_state", postgresql.JSONB(), nullable=True))

        op.execute(
            sa.text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_sync_state_integration_stream "
                "ON sync_state (integration_code, stream_name)"
            )
        )

    # --- canonical_sales._airbyte_loaded_at ---
    if "canonical_sales" in _tables(bind):
        cc = _cols(bind, "canonical_sales")
        if "_airbyte_loaded_at" not in cc:
            op.add_column(
                "canonical_sales",
                sa.Column("_airbyte_loaded_at", sa.DateTime(timezone=True), nullable=True),
            )


def downgrade() -> None:
    bind = op.get_bind()
    t = _tables(bind)

    if "canonical_sales" in t and "_airbyte_loaded_at" in _cols(bind, "canonical_sales"):
        op.drop_column("canonical_sales", "_airbyte_loaded_at")

    if "sync_state" in t:
        op.execute(sa.text("DROP INDEX IF EXISTS uq_sync_state_integration_stream"))
        for col in ("airbyte_state", "cursor_field", "sync_mode", "stream_name"):
            if col in _cols(bind, "sync_state"):
                op.drop_column("sync_state", col)
        op.create_unique_constraint("sync_state_integration_code_key", "sync_state", ["integration_code"])

    staging = [
        ("raw_ozon_postings_staging", "raw_ozon_staging"),
        ("raw_1c_orders_staging", "raw_1c_staging"),
        ("raw_google_sheet_orders_staging", "raw_sheet_staging"),
    ]
    cur = _tables(bind)
    for new_n, old_n in staging:
        if new_n in cur and old_n not in cur:
            for ac in ("_airbyte_meta", "_airbyte_extracted_at", "_airbyte_raw_id"):
                if ac in _cols(bind, new_n):
                    op.drop_column(new_n, ac)
            op.rename_table(new_n, old_n)
