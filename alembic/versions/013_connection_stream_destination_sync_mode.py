"""connection_stream.destination_sync_mode — режим записи в приёмник (дубликаты).

Revision ID: 013_connection_stream_destination_sync_mode
Revises: 012_drop_canonical_add_rules
Create Date: 2026-05-31
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "013_connection_stream_destination_sync_mode"
down_revision: Union[str, None] = "012_drop_canonical_add_rules"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables(bind) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


def _cols(bind, table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(bind).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    if "connection_stream" not in _tables(bind):
        return
    if "destination_sync_mode" not in _cols(bind, "connection_stream"):
        op.add_column(
            "connection_stream",
            sa.Column(
                "destination_sync_mode",
                sa.String(32),
                nullable=False,
                server_default=sa.text("'refresh_overwrite'"),
            ),
        )
        op.execute(
            sa.text(
                "UPDATE connection_stream SET destination_sync_mode = 'append' "
                "WHERE sync_mode = 'incremental'"
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    if "connection_stream" in _tables(bind) and "destination_sync_mode" in _cols(bind, "connection_stream"):
        op.drop_column("connection_stream", "destination_sync_mode")
