"""Phase 4: domain tables source, destination, connection, connection_stream; link sync_state; sync_run.domain_connection_id.

Revision ID: 008_phase4_source_destination_connection
Revises: 007_phase6_business_normalization
Create Date: 2026-05-03
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008_phase4_source_destination_connection"
down_revision: Union[str, None] = "007_phase6_business_normalization"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables(bind) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


def _cols(bind, table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(bind).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()

    if "source" not in _tables(bind):
        op.create_table(
            "source",
            sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
            sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspace.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("connector_code", sa.String(64), nullable=False),
            sa.Column("config_encrypted", sa.Text(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'active'")),
            sa.Column("created_by", sa.String(128), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
            sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_source_workspace_id", "source", ["workspace_id"], unique=False)

    if "destination" not in _tables(bind):
        op.create_table(
            "destination",
            sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
            sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspace.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("connector_code", sa.String(64), nullable=False),
            sa.Column("config_encrypted", sa.Text(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'active'")),
            sa.Column("created_by", sa.String(128), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
            sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_destination_workspace_id", "destination", ["workspace_id"], unique=False)

    if "connection" not in _tables(bind):
        op.create_table(
            "connection",
            sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
            sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspace.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("source_id", sa.BigInteger(), sa.ForeignKey("source.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("destination_id", sa.BigInteger(), sa.ForeignKey("destination.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'active'")),
            sa.Column("schedule_cron", sa.String(128), nullable=True),
            sa.Column("timezone", sa.String(64), nullable=False, server_default=sa.text("'UTC'")),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_by", sa.String(128), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        )
        op.create_index("ix_connection_workspace_id", "connection", ["workspace_id"], unique=False)
        op.create_index("ix_connection_source_id", "connection", ["source_id"], unique=False)
        op.create_index("ix_connection_destination_id", "connection", ["destination_id"], unique=False)

    if "connection_stream" not in _tables(bind):
        op.create_table(
            "connection_stream",
            sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
            sa.Column("connection_id", sa.BigInteger(), sa.ForeignKey("connection.id", ondelete="CASCADE"), nullable=False),
            sa.Column("stream_name", sa.String(128), nullable=False),
            sa.Column("sync_mode", sa.String(32), nullable=False, server_default=sa.text("'full_refresh'")),
            sa.Column("cursor_field", sa.String(256), nullable=True),
            sa.Column("primary_key", sa.String(512), nullable=True),
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("cursor_value", sa.Text(), nullable=True),
            sa.Column(
                "mapping_profile_id",
                sa.BigInteger(),
                sa.ForeignKey("mapping_profile.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.UniqueConstraint("connection_id", "stream_name", name="uq_connection_stream_name"),
        )
        op.create_index("ix_connection_stream_connection_id", "connection_stream", ["connection_id"], unique=False)

    if "sync_state" in _tables(bind) and "connection_stream_id" not in _cols(bind, "sync_state"):
        op.add_column(
            "sync_state",
            sa.Column(
                "connection_stream_id",
                sa.BigInteger(),
                sa.ForeignKey("connection_stream.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
        op.create_index("ix_sync_state_connection_stream_id", "sync_state", ["connection_stream_id"], unique=False)

    if "sync_run" in _tables(bind) and "domain_connection_id" not in _cols(bind, "sync_run"):
        op.add_column(
            "sync_run",
            sa.Column(
                "domain_connection_id",
                sa.BigInteger(),
                sa.ForeignKey("connection.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
        op.create_index("ix_sync_run_domain_connection_id", "sync_run", ["domain_connection_id"], unique=False)

    # Backfill from sync_state when domain model is empty (idempotent for re-run).
    op.execute(
        sa.text(
            """
            DO $$
            DECLARE
              wid int;
              dest_id bigint;
              src_id bigint;
              conn_id bigint;
              cs_id bigint;
              ic text;
              r2 record;
            BEGIN
              IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'sync_state') THEN
                RETURN;
              END IF;
              IF (SELECT COUNT(*) FROM connection) > 0 THEN
                RETURN;
              END IF;
              IF NOT EXISTS (SELECT 1 FROM sync_state LIMIT 1) THEN
                RETURN;
              END IF;

              SELECT id INTO wid FROM workspace WHERE code = 'main' ORDER BY id LIMIT 1;
              IF wid IS NULL THEN
                RETURN;
              END IF;

              INSERT INTO destination (workspace_id, name, connector_code, config_encrypted, status, created_at, updated_at)
              VALUES (wid, 'PostgreSQL Warehouse', 'postgres', '{}', 'active', NOW(), NOW())
              RETURNING id INTO dest_id;

              FOR ic IN SELECT DISTINCT integration_code FROM sync_state ORDER BY integration_code
              LOOP
                INSERT INTO source (workspace_id, name, connector_code, config_encrypted, status, created_at, updated_at)
                VALUES (wid, ic, ic, '{}', 'active', NOW(), NOW())
                RETURNING id INTO src_id;

                INSERT INTO connection (workspace_id, name, description, source_id, destination_id, status, schedule_cron, timezone, is_active, created_at, updated_at)
                VALUES (wid, ic || ' → warehouse', NULL, src_id, dest_id, 'active', NULL, 'UTC', true, NOW(), NOW())
                RETURNING id INTO conn_id;

                FOR r2 IN SELECT * FROM sync_state WHERE integration_code = ic ORDER BY stream_name
                LOOP
                  INSERT INTO connection_stream (connection_id, stream_name, sync_mode, cursor_field, primary_key, is_enabled, cursor_value, mapping_profile_id)
                  VALUES (
                    conn_id,
                    r2.stream_name,
                    COALESCE(r2.sync_mode, 'full_refresh'),
                    r2.cursor_field,
                    NULL,
                    true,
                    CASE
                      WHEN r2.cursor_value IS NULL THEN NULL
                      ELSE r2.cursor_value::text
                    END,
                    NULL
                  )
                  RETURNING id INTO cs_id;

                  UPDATE sync_state SET connection_stream_id = cs_id WHERE id = r2.id;
                END LOOP;
              END LOOP;

              UPDATE sync_run sr
              SET domain_connection_id = c.id
              FROM sync_state ss
              JOIN connection_stream cs ON cs.id = ss.connection_stream_id
              JOIN connection c ON c.id = cs.connection_id
              WHERE sr.connection_id = ss.id;
            END $$;
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    if "sync_run" in _tables(bind):
        if "domain_connection_id" in _cols(bind, "sync_run"):
            op.drop_index("ix_sync_run_domain_connection_id", table_name="sync_run")
            op.drop_column("sync_run", "domain_connection_id")
    if "sync_state" in _tables(bind):
        if "connection_stream_id" in _cols(bind, "sync_state"):
            op.drop_index("ix_sync_state_connection_stream_id", table_name="sync_state")
            op.drop_column("sync_state", "connection_stream_id")
    if "connection_stream" in _tables(bind):
        op.drop_table("connection_stream")
    if "connection" in _tables(bind):
        op.drop_table("connection")
    if "destination" in _tables(bind):
        op.drop_table("destination")
    if "source" in _tables(bind):
        op.drop_table("source")
