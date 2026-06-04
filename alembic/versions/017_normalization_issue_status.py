"""Статус resolution для normalization_issue (UI resolve/ignore).

Revision ID: 017_normalization_issue_status
Revises: 016_elt_normalization_issue_schema
Create Date: 2026-06-04
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "017_normalization_issue_status"
down_revision: Union[str, None] = "016_elt_normalization_issue_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _cols(bind, table: str) -> set[str]:
    import sqlalchemy as sa

    return {c["name"] for c in sa.inspect(bind).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    if "normalization_issue" not in sa.inspect(bind).get_table_names():
        return
    cols = _cols(bind, "normalization_issue")
    if "status" not in cols:
        op.add_column(
            "normalization_issue",
            sa.Column("status", sa.String(16), nullable=False, server_default="open"),
        )
    if "resolved_at" not in cols:
        op.add_column("normalization_issue", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True))
    if "resolution_note" not in cols:
        op.add_column("normalization_issue", sa.Column("resolution_note", sa.Text(), nullable=True))
    if "resolved_by" not in cols:
        op.add_column("normalization_issue", sa.Column("resolved_by", sa.String(128), nullable=True))
    op.execute(
        sa.text(
            "ALTER TABLE normalization_issue DROP CONSTRAINT IF EXISTS ck_normalization_issue_status"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE normalization_issue ADD CONSTRAINT ck_normalization_issue_status "
            "CHECK (status IN ('open', 'resolved', 'ignored'))"
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    if "normalization_issue" not in sa.inspect(bind).get_table_names():
        return
    cols = _cols(bind, "normalization_issue")
    op.execute(sa.text("ALTER TABLE normalization_issue DROP CONSTRAINT IF EXISTS ck_normalization_issue_status"))
    if "resolved_by" in cols:
        op.drop_column("normalization_issue", "resolved_by")
    if "resolution_note" in cols:
        op.drop_column("normalization_issue", "resolution_note")
    if "resolved_at" in cols:
        op.drop_column("normalization_issue", "resolved_at")
    if "status" in cols:
        op.drop_column("normalization_issue", "status")
