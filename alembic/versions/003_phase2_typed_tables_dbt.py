"""Phase 2: typed_canonical_sales for typing & deduping layer.

Revision ID: 003_phase2_typed
Revises: 002_phase1_airbyte
Create Date: 2026-04-08
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_phase2_typed"
down_revision: Union[str, None] = "002_phase1_airbyte"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables(bind) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


def upgrade() -> None:
    bind = op.get_bind()
    if "typed_canonical_sales" not in _tables(bind):
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
            sa.Column("_airbyte_extracted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("_airbyte_meta", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
            sa.PrimaryKeyConstraint("source_system", "source_record_id", name="pk_typed_canonical_sales"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if "typed_canonical_sales" in _tables(bind):
        op.drop_table("typed_canonical_sales")
