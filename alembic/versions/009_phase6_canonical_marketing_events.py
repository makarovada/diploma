"""Phase 6: canonical_marketing_events для Яндекс Метрики и маркетинговых источников.

Revision ID: 009_phase6_canonical_marketing_events
Revises: 008_phase4_source_destination_connection
Create Date: 2026-05-03
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "009_phase6_canonical_marketing_events"
down_revision: Union[str, None] = "008_phase4_source_destination_connection"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables(bind) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


def upgrade() -> None:
    bind = op.get_bind()
    if "canonical_marketing_events" in _tables(bind):
        return
    op.create_table(
        "canonical_marketing_events",
        sa.Column("source_system", sa.String(64), nullable=False),
        sa.Column("source_record_id", sa.String(512), nullable=False),
        sa.Column("counter_id", sa.String(64), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("event_datetime", sa.DateTime(timezone=True), nullable=True),
        sa.Column("client_id", sa.String(256), nullable=True),
        sa.Column("visit_id", sa.String(256), nullable=True),
        sa.Column("traffic_source", sa.Text(), nullable=True),
        sa.Column("utm_source", sa.String(256), nullable=True),
        sa.Column("utm_medium", sa.String(256), nullable=True),
        sa.Column("utm_campaign", sa.String(512), nullable=True),
        sa.Column("device", sa.String(128), nullable=True),
        sa.Column("browser", sa.String(128), nullable=True),
        sa.Column("region", sa.String(256), nullable=True),
        sa.Column("goal_id", sa.String(64), nullable=True),
        sa.Column("goal_name", sa.String(512), nullable=True),
        sa.Column("revenue", sa.Numeric(18, 4), nullable=True),
        sa.Column("currency", sa.String(16), nullable=True),
        sa.Column("_ingest_loaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("_ingest_meta", postgresql.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint("source_system", "source_record_id", name="pk_canonical_marketing_events"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if "canonical_marketing_events" in _tables(bind):
        op.drop_table("canonical_marketing_events")
