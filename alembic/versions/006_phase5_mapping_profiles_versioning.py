"""Phase 5: persisted mapping profiles with versions and activation.

Revision ID: 006_phase5_mapping_profiles_versioning
Revises: 005_phase4_sync_runs
Create Date: 2026-05-02
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006_phase5_mapping_profiles_versioning"
down_revision: Union[str, None] = "005_phase4_sync_runs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables(bind) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


def _cols(bind, table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(bind).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    tables = _tables(bind)

    # Preserve legacy structure if present.
    if "mapping_profile" in tables:
        cols = _cols(bind, "mapping_profile")
        if "profile_name" not in cols:
            if "mapping_profile_legacy" not in tables:
                op.rename_table("mapping_profile", "mapping_profile_legacy")
            tables = _tables(bind)

    if "mapping_profile" not in tables:
        op.create_table(
            "mapping_profile",
            sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
            sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspace.id", ondelete="CASCADE"), nullable=False),
            sa.Column("source_type", sa.String(64), nullable=False),
            sa.Column("stream_name", sa.String(128), nullable=False),
            sa.Column("profile_name", sa.String(128), nullable=False),
            sa.Column("active_version_id", sa.BigInteger(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
            sa.Column("updated_by", sa.String(128), nullable=True),
            sa.UniqueConstraint(
                "workspace_id",
                "source_type",
                "stream_name",
                "profile_name",
                name="uq_mapping_profile_scope_name",
            ),
        )

    if "mapping_profile_version" not in _tables(bind):
        op.create_table(
            "mapping_profile_version",
            sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
            sa.Column("profile_id", sa.BigInteger(), sa.ForeignKey("mapping_profile.id", ondelete="CASCADE"), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'draft'")),
            sa.Column("rules_json", postgresql.JSONB(), nullable=False),
            sa.Column("change_note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
            sa.Column("created_by", sa.String(128), nullable=True),
            sa.UniqueConstraint("profile_id", "version", name="uq_mapping_profile_version_num"),
            sa.CheckConstraint("status IN ('draft', 'published', 'archived')", name="ck_mapping_profile_version_status"),
        )

    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_mapping_profile_workspace ON mapping_profile (workspace_id)"))
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_mapping_profile_scope ON mapping_profile (workspace_id, source_type, stream_name)"
        )
    )
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_mapping_profile_active_version ON mapping_profile (active_version_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_mapping_profile_updated_at ON mapping_profile (updated_at)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_mapping_profile_version_status ON mapping_profile_version (status)"))

    op.execute(
        sa.text(
            "DO $$ BEGIN "
            "IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_mapping_profile_active_version') THEN "
            "ALTER TABLE mapping_profile "
            "ADD CONSTRAINT fk_mapping_profile_active_version "
            "FOREIGN KEY (active_version_id) REFERENCES mapping_profile_version(id) ON DELETE SET NULL; "
            "END IF; END $$;"
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    tables = _tables(bind)
    if "mapping_profile_version" in tables:
        op.drop_table("mapping_profile_version")
    if "mapping_profile" in tables:
        op.drop_table("mapping_profile")
    if "mapping_profile_legacy" in tables:
        op.rename_table("mapping_profile_legacy", "mapping_profile")
