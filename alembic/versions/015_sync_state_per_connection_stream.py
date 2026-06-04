"""sync_state: одна строка на connection_stream (не на integration_code+stream_name).

Revision ID: 015_sync_state_per_connection_stream
Revises: 014_workspace_permissions_acl
Create Date: 2026-06-03
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "015_sync_state_per_connection_stream"
down_revision: Union[str, None] = "014_workspace_permissions_acl"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables(bind) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


def upgrade() -> None:
    bind = op.get_bind()
    if "sync_state" not in _tables(bind):
        return

    op.execute(sa.text("DROP INDEX IF EXISTS uq_sync_state_integration_stream"))

    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_sync_state_connection_stream_id
            ON sync_state (connection_stream_id)
            WHERE connection_stream_id IS NOT NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_sync_state_integration_stream_legacy
            ON sync_state (integration_code, stream_name)
            WHERE connection_stream_id IS NULL
            """
        )
    )

    if "connection_stream" not in _tables(bind) or "connection" not in _tables(bind) or "source" not in _tables(bind):
        return

    op.execute(
        sa.text(
            """
            INSERT INTO sync_state (
              integration_code, stream_name, sync_mode, cursor_field,
              cursor_value, ingest_state, last_success_at, updated_at,
              connection_stream_id, workspace_id
            )
            SELECT
              s.connector_code,
              cs.stream_name,
              cs.sync_mode,
              cs.cursor_field,
              '{"cursor": null, "via": "elt_domain_backfill"}',
              '{"cursor": null, "rows_emitted": 0, "via": "elt_domain_backfill"}',
              NULL,
              NOW(),
              cs.id,
              c.workspace_id
            FROM connection_stream cs
            JOIN connection c ON c.id = cs.connection_id
            JOIN source s ON s.id = c.source_id
            WHERE cs.is_enabled IS TRUE
              AND NOT EXISTS (
                SELECT 1 FROM sync_state ss WHERE ss.connection_stream_id = cs.id
              )
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    if "sync_state" not in _tables(bind):
        return
    op.execute(sa.text("DROP INDEX IF EXISTS uq_sync_state_connection_stream_id"))
    op.execute(sa.text("DROP INDEX IF EXISTS uq_sync_state_integration_stream_legacy"))
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_sync_state_integration_stream
            ON sync_state (integration_code, stream_name)
            """
        )
    )
