"""sync_state: CASCADE при удалении connection_stream (не SET NULL → legacy unique).

Revision ID: 018_sync_state_cascade_on_stream_delete
Revises: 017_normalization_issue_status
Create Date: 2026-06-14
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "018_sync_state_cascade_on_stream_delete"
down_revision: Union[str, None] = "017_normalization_issue_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "sync_state" not in tables or "connection_stream" not in tables:
        return
    op.execute(
        sa.text(
            "ALTER TABLE sync_state DROP CONSTRAINT IF EXISTS sync_state_connection_stream_id_fkey"
        )
    )
    op.create_foreign_key(
        "sync_state_connection_stream_id_fkey",
        "sync_state",
        "connection_stream",
        ["connection_stream_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "sync_state" not in tables or "connection_stream" not in tables:
        return
    op.execute(
        sa.text(
            "ALTER TABLE sync_state DROP CONSTRAINT IF EXISTS sync_state_connection_stream_id_fkey"
        )
    )
    op.create_foreign_key(
        "sync_state_connection_stream_id_fkey",
        "sync_state",
        "connection_stream",
        ["connection_stream_id"],
        ["id"],
        ondelete="SET NULL",
    )
